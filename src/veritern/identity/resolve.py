import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

import idna
import tldextract

_suffix = tldextract.TLDExtract(
    suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True
)


def normalize_url(value: str) -> str:
    value = value.strip()
    if len(value) > 2048 or re.search(r"[\x00-\x20\\]", value):
        raise ValueError("Enter a public website URL")
    parsed = urlsplit(value if "://" in value else "https://" + value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only HTTP(S) websites are supported")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 80, 443)
    ):
        raise ValueError("Credentials and nonstandard ports are not accepted")
    host = parsed.hostname.rstrip(".").lower()
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global or ip.is_multicast:
            raise ValueError("Destination must be public")
        host = f"[{ip}]" if ip.version == 6 else str(ip)
    except ValueError:
        if ":" in host or re.fullmatch(r"[\d.]+", host) or host.startswith("0x"):
            raise ValueError("Invalid or nonpublic address") from None
        host = idna.encode(host, uts46=True).decode("ascii")
        if "." not in host or host.endswith((".localhost", ".local", ".test", ".internal")):
            raise ValueError("A public domain is required") from None
    netloc = host + (f":{parsed.port}" if parsed.port else "")
    # Query strings may contain credentials; this application accepts public path URLs only.
    return urlunsplit((parsed.scheme, netloc, parsed.path or "/", "", ""))


def domain(url: str) -> str:
    host = urlsplit(url if "://" in url else "https://" + url).hostname or ""
    result = _suffix(host)
    return result.top_domain_under_public_suffix or host


def in_scope(text: str, target_domain: str, program: str) -> bool:
    # Name-only matches never establish identity. Explicit domain or specific program required.
    target = target_domain.lower()
    domain_match = bool(re.search(r"(?<![\w.-])" + re.escape(target) + r"(?![\w.-])", text.lower()))
    program_match = (
        len(program.split()) >= 3
        and program.lower() != "unspecified program"
        and program.lower() in text.lower()
    )
    return domain_match or program_match
