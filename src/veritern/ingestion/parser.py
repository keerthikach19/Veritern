import base64
import json
import subprocess
import sys
from pathlib import Path

from veritern.config import Settings


def parse_upload(data: bytes, filename: str, settings: Settings) -> dict:
    if not data or len(data) > settings.upload_max_bytes:
        raise ValueError("Upload is empty or exceeds the byte limit")
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".png", ".jpg", ".jpeg", ".txt", ".eml"):
        raise ValueError("Only PDF, PNG/JPEG, TXT and EML are supported")
    request = {
        "data": base64.b64encode(data).decode(),
        "suffix": suffix,
        "pdf_pages": settings.pdf_max_pages,
        "ocr_pages": settings.ocr_max_pages_per_case,
        "pixels": settings.image_max_pixels,
    }
    try:
        process = subprocess.run(
            [sys.executable, "-m", "veritern.ingestion.worker"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        result = json.loads(process.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        raise ValueError("Document parsing timed out or failed; paste the relevant text") from None
    if "error" in result:
        raise ValueError(result["error"])
    return result
