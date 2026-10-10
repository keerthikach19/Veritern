import re


def redact(text: str) -> str:
    patterns = [
        (r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL]"),
        (r"(?<!\w)(?:\+\d{1,3}[ -]?)?(?:\d[ -]?){10,16}(?!\w)", "[PHONE/ID]"),
        (r"(?i)\b(?:gsk_|sk-)[A-Za-z0-9_-]{12,}\b", "[SECRET]"),
        (
            r"(?im)\b(password|token|secret|account number|bank account|address|signature|aadhaar|pan)\s*[:=]\s*[^\n]+",
            "[SENSITIVE FIELD]",
        ),
        (r"(?i)\b[A-Z0-9._-]+@(?:upi|paytm|ybl|okaxis|oksbi|okhdfcbank)\b", "[PAYMENT ID]"),
        (r"https?://[^\s]+\?[^\s]+", "[URL WITH QUERY REMOVED]"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text
