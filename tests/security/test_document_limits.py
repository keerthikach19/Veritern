import base64
import io

import pytest
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from veritern.ingestion.parser import parse_upload
from veritern.ingestion.worker import parse


def request(raw, suffix, **changes):
    return {
        "data": base64.b64encode(raw).decode(),
        "suffix": suffix,
        "pdf_pages": 15,
        "ocr_pages": 6,
        "pixels": 20000000,
        **changes,
    }


def test_text_pdf_skips_ocr(settings):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 40 720 Td (This is a fictional internship offer with an optional certificate fee of INR 50.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    result = parse_upload(output.getvalue(), "offer.pdf", settings)
    assert "INR 50" in result["text"]
    assert result["ocr_pages"] == 0 and not result["ocr_review_required"]


def test_page_limit_before_ocr():
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=612, height=792)
    output = io.BytesIO()
    writer.write(output)
    with pytest.raises(ValueError, match="page limit"):
        parse(request(output.getvalue(), ".pdf", pdf_pages=2))


def test_image_pixel_limit_and_missing_ocr(monkeypatch):
    output = io.BytesIO()
    Image.new("RGB", (50, 50)).save(output, format="PNG")
    with pytest.raises((ValueError, Image.DecompressionBombError)):
        parse(request(output.getvalue(), ".png", pixels=100))
    monkeypatch.setattr("veritern.ingestion.worker.shutil.which", lambda _: None)
    with pytest.raises(ValueError, match="Tesseract unavailable"):
        parse(request(output.getvalue(), ".png"))


def test_parser_timeout(settings, monkeypatch):
    import subprocess

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("parser", 45)

    monkeypatch.setattr("veritern.ingestion.parser.subprocess.run", timeout)
    with pytest.raises(ValueError, match="timed out"):
        parse_upload(b"text", "offer.txt", settings)
