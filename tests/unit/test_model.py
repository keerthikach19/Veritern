import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import groq
import httpx
import pytest

from veritern.demo import new_demo
from veritern.llm.client import (
    AnalysisUnavailable,
    Extracted,
    Extraction,
    GroqInference,
    validate_extraction,
)
from veritern.schemas import FactKind, Usage


def item(case, **changes):
    values = dict(
        source_id=case.sources[0].id,
        quote=case.sources[0].text,
        kind=FactKind.NO_FEE,
        program=case.program.title,
        batch="October 2026",
        event_date="2026-10-01",
        due_date=None,
        amount_minor=None,
        currency=None,
        mandatory=None,
        disclosed_before_joining=None,
        condition=None,
        benefit="certificate",
        attribution="advertised",
    )
    values.update(changes)
    return Extracted(**values)


@pytest.mark.parametrize(
    "change",
    [
        {"source_id": "missing"},
        {"quote": "invented evidence"},
        {"program": "Other entity"},
        {"amount_minor": 50000},
        {"event_date": "2024-01-01"},
        {"batch": "2021"},
        {"condition": "invented condition"},
        {"attribution": "authoritative"},
    ],
)
def test_invalid_model_evidence_rejected(change):
    case = new_demo(stage="initial")
    with pytest.raises(ValueError):
        validate_extraction(Extraction(claims=[item(case, **change)]), case)


def test_exact_valid_quote_accepted():
    case = new_demo(stage="initial")
    claims, spans = validate_extraction(Extraction(claims=[item(case)]), case)
    assert len(claims) == 1 and len(spans) == 1


def test_negation_and_up_to():
    case = new_demo("conditional_pay")
    with pytest.raises(ValueError):
        validate_extraction(
            Extraction(claims=[item(case, kind=FactKind.GUARANTEE, event_date=None)]), case
        )
    case.sources[0].text = "I was never asked for money in the October 2026 internship."
    with pytest.raises(ValueError):
        validate_extraction(
            Extraction(claims=[item(case, kind=FactKind.FEE, event_date=None)]), case
        )


def test_strict_schema_requires_all_fields():
    schema = Extraction.model_json_schema()
    for obj in [schema, *schema.get("$defs", {}).values()]:
        if obj.get("type") == "object":
            assert obj["additionalProperties"] is False
            assert set(obj["required"]) == set(obj["properties"])


async def test_private_text_without_consent_never_sent(settings):
    case = new_demo(stage="initial")
    case.mode = "live"
    case.sources[0].kind = "private"
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock())))
    claims, spans, _ = await GroqInference(settings, client).extract(
        case, Usage(), time.monotonic() + 10, lambda: False
    )
    assert not claims and not spans
    client.chat.completions.create.assert_not_called()


@pytest.mark.parametrize("status", [401, 403, 429, 500])
async def test_provider_error_bounded(settings, status):
    case = new_demo(stage="initial")
    case.mode = "live"
    settings.groq_max_attempts = 1
    error = groq.APIStatusError(
        "redacted",
        response=httpx.Response(status, request=httpx.Request("POST", "https://api.groq.com")),
        body=None,
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=error)))
    )
    usage = Usage()
    with pytest.raises(AnalysisUnavailable):
        await GroqInference(settings, client).extract(
            case, usage, time.monotonic() + 10, lambda: False
        )
    assert usage.calls == 1


async def test_valid_model_response_and_budget(settings):
    case = new_demo(stage="initial")
    case.mode = "live"
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=Extraction(claims=[item(case)]).model_dump_json()),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50),
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response)))
    )
    usage = Usage()
    claims, _, _ = await GroqInference(settings, client).extract(
        case, usage, time.monotonic() + 10, lambda: False
    )
    assert claims and usage.input_tokens == 100 and usage.output_tokens == 50
    with pytest.raises(AnalysisUnavailable):
        await GroqInference(settings, client).extract(
            case, Usage(calls=3), time.monotonic() + 10, lambda: False
        )
    assert client.chat.completions.create.call_count == 1


@pytest.mark.parametrize(
    "content,finish", [("not json", "stop"), (json.dumps({"claims": []}), "length")]
)
async def test_invalid_output_never_becomes_freeform(settings, content, finish):
    case = new_demo(stage="initial")
    case.mode = "live"
    response = SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish, message=SimpleNamespace(content=content))],
        usage=None,
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=response)))
    )
    with pytest.raises(AnalysisUnavailable):
        await GroqInference(settings, client).extract(
            case, Usage(), time.monotonic() + 10, lambda: False
        )
