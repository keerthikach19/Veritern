import json

import pytest
from pydantic import ValidationError

from veritern.reference import (
    ReferenceCase,
    export_reference,
    identify_reference,
    load_references,
    reference_for_url,
    review_reference,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://internpe.in/", "internpe"),
        ("internshipstudio.com", "internship_studio"),
        ("https://www.oasisinfobyte.com/", "oasis_infobyte"),
        ("https://oasisinfobyte.in", "oasis_infobyte"),
        ("https://www.tcs.com/careers", "tcs"),
        ("https://careers.wipro.com/", "wipro"),
    ],
)
def test_exact_domains_resolve_with_no_network(url, expected):
    assert reference_for_url(url).id == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://tcs.com.evil.org",
        "https://tcs-careers-india.in",
        "https://unknown-example.org",
        "https://internpein.com",
    ],
)
def test_unlisted_or_lookalike_domain_never_gets_another_company_result(url):
    assert reference_for_url(url) is None


def test_all_quotes_are_from_supplied_text_and_no_verification_is_invented():
    for case in load_references().values():
        result = review_reference(case)
        assert result.verification_required
        assert not result.model_executed
        assert not result.ocr_executed
        assert not result.live_checks_executed
        assert all(phrase in case.reference_text for phrase in result.matched_phrases)
        assert all(note.quote in case.reference_text for note in case.notes)
        assert result.classification != "VERIFIED GENUINE"
        payload = json.loads(export_reference(case))
        assert payload["provenance"]["ocr"].startswith("Not run")
        assert payload["result"]["evidence_basis"].startswith("Provided reference text")


def test_wipro_positive_structure_is_still_unauthenticated():
    result = review_reference(load_references()["wipro"])
    assert result.classification == "UNKNOWN"
    assert result.verification_required


@pytest.mark.parametrize(
    "text",
    [
        "InternPE",
        "Wipro",
        "INTERNSHIP OFFER LETTER",
        "training certificate stipend joining date",
        "Internship Coordinator",
    ],
)
def test_single_name_or_generic_phrase_cannot_identify_a_letter(text):
    assert identify_reference(text) == (None, [])


def test_multiple_indicators_identify_but_mixed_companies_abstain():
    cases = load_references()
    for case in cases.values():
        # The short phrase list excludes comparative notes mentioning another company.
        text = "\n".join(case.identifying_phrases)
        assert identify_reference(text)[0] == case.id
    mixed = "\n".join(cases["wipro"].identifying_phrases + cases["tcs"].identifying_phrases)
    assert identify_reference(mixed) == (None, [])


def test_schema_rejects_unsupported_quotes():
    record = load_references()["internpe"].model_dump()
    record["notes"][0]["quote"] = "This sentence was never supplied."
    with pytest.raises(ValidationError, match="exact source excerpt"):
        ReferenceCase.model_validate(record)
