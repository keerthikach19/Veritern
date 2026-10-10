import json

import pytest

from veritern.demo import new_demo
from veritern.ingestion.parser import parse_upload
from veritern.ingestion.redact import redact
from veritern.reporting.reports import export_json, export_markdown


def test_redacts_secrets_and_preserves_fee():
    result = redact("Email alice@example.com phone 9876543210 fee INR 50\npassword: secret123")
    assert "alice" not in result and "9876543210" not in result and "secret123" not in result
    assert "INR 50" in result


def test_text_and_email_ingestion(settings):
    assert (
        "hello" in parse_upload(b"hello internship terms", "../../evidence.txt", settings)["text"]
    )
    eml = b"From: alice@example.com\nSubject: Internship\nContent-Type: text/plain\n\nAn optional certificate costs INR 50."
    parsed = parse_upload(eml, "offer.eml", settings)
    assert "unauthenticated" in parsed["text"]
    assert not parsed["ocr_review_required"]


@pytest.mark.parametrize(
    "data,name",
    [
        (b"PKzip", "x.zip"),
        (b"MZexecutable", "x.pdf"),
        (b"not an image", "x.png"),
        (b"\x00\xff", "x.txt"),
        (b"", "x.txt"),
    ],
)
def test_corrupt_or_unsupported_uploads(settings, data, name):
    with pytest.raises(ValueError):
        parse_upload(data, name, settings)


def test_report_excludes_raw_source_and_owner():
    case = new_demo()
    case.sources[0].text += "\nPrivate raw data not in evidence spans"
    report = export_json(case)
    assert "Private raw data" not in report and '"owner"' not in report
    assert json.loads(report)["mode"] == "demo"
    assert "FICTIONAL" in export_markdown(case)
