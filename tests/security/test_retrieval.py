import socket

import httpx
import pytest

from veritern.identity import domain, normalize_url
from veritern.retrieval.safe import (
    Fetcher,
    PublicBackend,
    UnsafeDestination,
    public_addresses,
    safe_transport,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://169.254.169.254",
        "http://[::1]",
        "http://[::ffff:127.0.0.1]",
        "http://2130706433",
        "http://0x7f000001",
        "http://0177.0.0.1",
        "http://localhost",
        "http://x.local",
        "http://x.test",
        "file:///etc/passwd",
        "ftp://example.com",
        "https://user:pass@example.com",
        "https://example.com:123",
        "https://example.com\\@localhost",
        "http://127%2e0%2e0%2e1",
    ],
)
def test_unsafe_urls(url):
    with pytest.raises(ValueError):
        normalize_url(url)


def test_psl_and_credentials_stripping():
    assert domain("https://jobs.example.co.uk") == "example.co.uk"
    assert domain("https://alice.github.io") != domain("https://bob.github.io")
    assert normalize_url("EXAMPLE.com/path?token=secret#x") == "https://example.com/path"


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "169.254.169.254",
        "::1",
        "fc00::1",
        "::ffff:10.1.1.1",
        "224.0.0.1",
        "100.64.0.1",
    ],
)
async def test_dns_blocks_all_nonpublic(monkeypatch, address):
    import asyncio

    async def fake(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", fake)
    with pytest.raises(UnsafeDestination):
        await public_addresses("example.com", 443)


async def test_validated_ip_is_actual_connection_destination(monkeypatch):
    import veritern.retrieval.safe as module

    called = []

    async def resolve(host, port):
        return ["93.184.216.34"]

    class Fake:
        async def connect_tcp(self, host, *args):
            called.append(host)
            return "stream"

    monkeypatch.setattr(module, "public_addresses", resolve)
    assert await PublicBackend(Fake()).connect_tcp("example.com", 443) == "stream"
    assert called == ["93.184.216.34"]
    assert isinstance(safe_transport()._pool._network_backend, PublicBackend)


async def test_private_redirect_blocked(settings):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"})

    source, _ = await Fetcher(settings, httpx.MockTransport(handler)).fetch(
        "https://example.com", "example.com"
    )
    assert source.access == "blocked"
    assert not any("127.0.0.1" in url for url in seen)


@pytest.mark.parametrize(
    "behavior,expected",
    [
        ("robots", "robots_disallowed"),
        ("compressed", "unsupported"),
        ("large", "unsupported"),
        ("403", "blocked"),
        ("js", "unsupported"),
    ],
)
async def test_access_and_byte_limits(settings, behavior, expected):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nDisallow: /"
                if behavior == "robots"
                else "User-agent: *\nAllow: /",
            )
        if behavior == "403":
            return httpx.Response(403)
        headers = {"content-type": "text/html"}
        if behavior == "compressed":
            headers["content-encoding"] = "br"
        if behavior == "large":
            headers["content-length"] = "99999999"
        return httpx.Response(200, headers=headers, content=b"<script>app()</script>")

    source, _ = await Fetcher(settings, httpx.MockTransport(handler)).fetch(
        "https://example.com", "example.com"
    )
    assert source.access == expected


async def test_demo_zero_network(settings):
    settings.app_mode = "demo"
    source, _ = await Fetcher(settings).fetch("https://example.com", "example.com")
    assert source.access == "not_attempted"


@pytest.mark.parametrize(
    "destination", ["https://example.com/policy.txt", "https://rules.example.org/robots.txt"]
)
async def test_robots_redirect_rules_apply_to_original_site(settings, destination):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if str(request.url) == "https://example.com/robots.txt":
            return httpx.Response(301, headers={"location": destination})
        if str(request.url) == destination:
            return httpx.Response(200, text="User-agent: *\nDisallow: /")
        raise AssertionError("Disallowed page must not be fetched")

    source, _ = await Fetcher(settings, httpx.MockTransport(handler)).fetch(
        "https://example.com", "example.com"
    )
    assert source.access == "robots_disallowed"
    assert seen == ["https://example.com/robots.txt", destination]


@pytest.mark.parametrize("failure", ["network", "503", "403", "redirect_loop", "html"])
async def test_unreadable_policy_is_not_a_site_disallow(settings, failure):
    def handler(request):
        assert request.url.path == "/robots.txt"
        if failure == "network":
            raise httpx.ConnectError("Network disabled", request=request)
        if failure == "redirect_loop":
            return httpx.Response(302, headers={"location": "/robots.txt"})
        if failure == "html":
            return httpx.Response(200, text="<html>Challenge</html>")
        return httpx.Response(int(failure))

    source, _ = await Fetcher(settings, httpx.MockTransport(handler)).fetch(
        "https://example.com", "example.com"
    )
    assert source.access == "robots_unavailable"
    assert "No inference about legitimacy" in source.note


async def test_private_robots_redirect_never_requested(settings):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/robots.txt"})

    source, _ = await Fetcher(settings, httpx.MockTransport(handler)).fetch(
        "https://example.com", "example.com"
    )
    assert source.access == "blocked"
    assert seen == ["https://example.com/robots.txt"]


@pytest.mark.parametrize("bomb", [False, True])
async def test_gzip_is_bounded_while_decompressing(settings, bomb):
    import gzip

    class Wire(httpx.AsyncByteStream):
        async def __aiter__(self):
            payload = (
                b"x" * (settings.fetch_max_bytes + 1)
                if bomb
                else b"This example website provides training with supervised project work."
            )
            yield gzip.compress(payload)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200, headers={"content-type": "text/plain", "content-encoding": "gzip"}, stream=Wire()
        )

    source, _ = await Fetcher(settings, httpx.MockTransport(handler)).fetch(
        "https://example.com", "example.com"
    )
    assert source.access == ("unsupported" if bomb else "retrieved")


async def test_connection_failure_is_not_reported_as_access_block(settings):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        raise httpx.ConnectError("Connection failed", request=request)

    source, _ = await Fetcher(settings, httpx.MockTransport(handler)).fetch(
        "https://example.com", "example.com"
    )
    assert source.access == "connection_failed"


async def test_pinned_backend_tries_another_validated_address(monkeypatch):
    import httpcore

    import veritern.retrieval.safe as module

    async def resolve(*args):
        return ["93.184.216.34", "93.184.216.35"]

    seen = []

    class Fake:
        async def connect_tcp(self, address, *args):
            seen.append(address)
            if len(seen) == 1:
                raise httpcore.ConnectError("Unavailable")
            return "connected"

    monkeypatch.setattr(module, "public_addresses", resolve)
    assert await PublicBackend(Fake()).connect_tcp("example.com", 443) == "connected"
    assert seen == ["93.184.216.34", "93.184.216.35"]


async def test_company_footer_survives_text_extraction(settings):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><body><main><p>Welcome to our internship program for students.</p></main><footer>Owned and operated by Example Learning. Registered under UDYAM-AA-00-1234567.</footer><script>secretScriptCode()</script></body></html>",
        )

    source, _ = await Fetcher(settings, httpx.MockTransport(handler)).fetch(
        "https://example.com", "example.com"
    )
    assert "UDYAM-AA-00-1234567" in source.text
    assert "secretScriptCode" not in source.text
