"""Subprocess boundary: no logging, URL fetches, active content, or persisted uploads."""

import base64
import io
import json
import shutil
import sys
import warnings
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr

from PIL import Image


def ocr(image):
    if not shutil.which("tesseract"):
        raise ValueError("Tesseract unavailable; paste the image's text instead")
    import pytesseract

    return pytesseract.image_to_string(image, lang="eng", timeout=15)


def parse(request):
    raw = base64.b64decode(request["data"], validate=True)
    suffix = request["suffix"]
    used_ocr = False
    ocr_pages = 0
    text = ""
    if suffix == ".pdf":
        if not raw.startswith(b"%PDF-"):
            raise ValueError("PDF signature does not match")
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted or len(reader.pages) > request["pdf_pages"]:
            raise ValueError("Encrypted PDF or page limit exceeded")
        for n, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if len(page_text.strip()) < 40:
                if ocr_pages >= request["ocr_pages"]:
                    raise ValueError("OCR page budget reached; paste missing text")
                import pypdfium2

                with pypdfium2.PdfDocument(raw) as document:
                    rendered = document[n]
                    width, height = rendered.get_size()
                    if width * height * 4 > request["pixels"]:
                        raise ValueError("Rendered PDF page exceeds pixel limit")
                    bitmap = rendered.render(scale=2)
                    page_text = ocr(bitmap.to_pil())
                    bitmap.close()
                    rendered.close()
                used_ocr = True
                ocr_pages += 1
            text += f"\n[Page {n + 1}]\n{page_text}\n"
    elif suffix in (".png", ".jpg", ".jpeg"):
        if not (raw.startswith(b"\x89PNG\r\n\x1a\n") or raw.startswith(b"\xff\xd8\xff")):
            raise ValueError("Image signature does not match")
        Image.MAX_IMAGE_PIXELS = request["pixels"]
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > request["pixels"]:
                raise ValueError("Image exceeds pixel limit")
            image.load()
            text = "[Image 1]\n" + ocr(image)
        used_ocr = True
        ocr_pages = 1
    elif suffix == ".eml":
        message = BytesParser(policy=policy.default).parsebytes(raw)
        if not message.get("From") and not message.get("Subject"):
            raise ValueError("Email headers not found")
        text = f"From (unauthenticated): {message.get('From', '')}\nReply-To: {message.get('Reply-To', '')}\nSubject: {message.get('Subject', '')}\n"
        for header in ("From", "Reply-To"):
            address = parseaddr(str(message.get(header, "")))[1]
            if "@" in address:
                sender_domain = address.rsplit("@", 1)[1].lower()
                text += f"{header} domain (unauthenticated): {sender_domain}\n"
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                text += "\n[Attachment omitted]\n"
            elif part.get_content_type() == "text/plain":
                text += str(part.get_content()) + "\n"
    else:
        text = raw.decode("utf-8-sig", errors="strict")
        if "\x00" in text or text.lstrip().startswith(("<html", "<!DOCTYPE", "MZ")):
            raise ValueError("Not a plain UTF-8 text document")
    if not text.strip():
        raise ValueError("No readable text; paste the relevant passages")
    if len(text) > 60000:
        raise ValueError("Extracted text exceeds budget; provide a shorter excerpt")
    return {"text": text, "ocr_review_required": used_ocr, "ocr_pages": ocr_pages}


if __name__ == "__main__":
    try:
        print(json.dumps(parse(json.loads(sys.stdin.read())), ensure_ascii=True))
    except Exception as exc:
        message = (
            str(exc) if isinstance(exc, ValueError) else "Unable to parse document; use pasted text"
        )
        print(json.dumps({"error": message}))
