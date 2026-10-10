import asyncio
import ipaddress
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpcore
import httpx
import trafilatura
from httpcore._backends.anyio import AnyIOBackend

from veritern.config import Settings
from veritern.identity import domain, normalize_url
from veritern.schemas import Access, Source

USER_AGENT = "Veritern/0.1 (+evidence research; respects robots.txt)"
RESTRICTED = {"linkedin.com", "glassdoor.com", "reddit.com"}


class UnsafeDestination(ValueError):
    pass


async def public_addresses(host: str, port: int) -> list[str]:
    rows = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = sorted({row[4][0] for row in rows})
    if not addresses:
        raise UnsafeDestination("No public address")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            not ip.is_global
            or ip.is_multicast
            or (ip.version == 6 and ip.ipv4_mapped and not ip.ipv4_mapped.is_global)
        ):
            raise UnsafeDestination("Nonpublic destination blocked")
    return addresses


class PublicBackend(httpcore.AsyncNetworkBackend):
    """httpcore retains hostname for TLS/SNI; only TCP gets the validated IP."""

    def __init__(self, backend=None):
        self.backend = backend or AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        async with asyncio.timeout(timeout or 12):
            addresses = await public_addresses(host, port)
            # Numeric literal passed to the socket connector: no second hostname DNS lookup.
            return await self.backend.connect_tcp(
                addresses[0], port, timeout, local_address, socket_options
            )

    async def connect_unix_socket(self, *args, **kwargs):
        raise UnsafeDestination("Unix sockets are disabled")

    async def sleep(self, seconds):
        await asyncio.sleep(seconds)


def safe_transport() -> httpx.AsyncHTTPTransport:
    transport = httpx.AsyncHTTPTransport(retries=0, trust_env=False)
    # Deliberate pinned compatibility boundary; HTTPX/httpcore versions are locked and tested.
    transport._pool._network_backend = PublicBackend()
    return transport


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.extend(v for k, v in attrs if k == "href" and v)


class Fetcher:
    def __init__(self, settings: Settings, transport=None):
        self.settings = settings
        self.transport = transport
        self.host_locks: dict[str, asyncio.Lock] = {}
        self.robots: dict[str, RobotFileParser | bool] = {}

    async def _read(self, client, url, max_bytes):
        async with client.stream("GET", url) as response:
            # Identity encoding prevents decompression bombs. Refuse servers ignoring it.
            if response.headers.get("content-encoding", "identity").lower() not in ("identity", ""):
                raise ValueError("Compressed response unsupported")
            if int(response.headers.get("content-length", "0")) > max_bytes:
                raise ValueError("Response exceeds byte budget")
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise ValueError("Response exceeds byte budget")
            return response, bytes(data)

    async def _allowed(self, client, url):
        origin = str(httpx.URL(url).copy_with(path="/robots.txt", query=None, fragment=None))
        if origin not in self.robots:
            try:
                response, raw = await self._read(client, origin, 200000)
                if response.status_code == 404:
                    self.robots[origin] = True
                elif response.status_code != 200:
                    self.robots[origin] = False
                else:
                    parser = RobotFileParser()
                    parser.parse(raw.decode("utf-8", errors="replace").splitlines())
                    self.robots[origin] = parser
            except (httpx.HTTPError, ValueError, OSError):
                self.robots[origin] = False
        policy = self.robots[origin]
        return policy if isinstance(policy, bool) else policy.can_fetch("Veritern", url)

    async def fetch(self, url: str, target_domain: str) -> tuple[Source, list[str]]:
        source = Source(
            title="Website evidence", url=url, kind="third_party", access=Access.NOT_ATTEMPTED
        )
        if self.settings.app_mode == "demo":
            source.note = "Demo performs no network requests"
            return source, []
        try:
            url = normalize_url(url)
            source.url = url
            source.publisher = domain(url)
            if domain(url) in RESTRICTED:
                source.access = Access.BLOCKED
                source.note = (
                    "Platform not checked directly; use indexed links or consented pasted text"
                )
                return source, []
            async with asyncio.timeout(self.settings.fetch_timeout_seconds):
                async with httpx.AsyncClient(
                    transport=self.transport or safe_transport(),
                    trust_env=False,
                    follow_redirects=False,
                    timeout=self.settings.fetch_timeout_seconds,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept-Encoding": "identity",
                        "Accept": "text/html,text/plain",
                    },
                ) as client:
                    for _ in range(self.settings.max_redirects + 1):
                        host = urlsplit(url).hostname
                        async with self.host_locks.setdefault(host, asyncio.Lock()):
                            if not await self._allowed(client, url):
                                source.access = Access.ROBOTS
                                source.note = "Robots disallow or policy could not be checked"
                                return source, []
                            policy = self.robots.get(
                                str(
                                    httpx.URL(url).copy_with(
                                        path="/robots.txt", query=None, fragment=None
                                    )
                                )
                            )
                            delay = (
                                policy.crawl_delay("Veritern")
                                if isinstance(policy, RobotFileParser)
                                else None
                            )
                            await asyncio.sleep(max(0.25, delay or 0))
                            response, raw = await self._read(
                                client, url, self.settings.fetch_max_bytes
                            )
                        if response.is_redirect:
                            url = normalize_url(urljoin(url, response.headers.get("location", "")))
                            if domain(url) in RESTRICTED:
                                source.access = Access.BLOCKED
                                return source, []
                            continue
                        source.url = url
                        source.publisher = domain(url)
                        if response.status_code in (401, 403, 429):
                            source.access = Access.BLOCKED
                            source.note = f"Access restricted ({response.status_code})"
                            return source, []
                        if response.status_code != 200:
                            source.access = Access.NOT_FOUND
                            source.note = f"HTTP {response.status_code}"
                            return source, []
                        ctype = response.headers.get("content-type", "").split(";")[0]
                        if ctype not in ("text/html", "text/plain", "application/xhtml+xml"):
                            source.access = Access.UNSUPPORTED
                            source.note = (
                                "Only public HTML/text pages fetched; PDF may be added manually"
                            )
                            return source, []
                        html = raw.decode("utf-8", errors="replace")
                        text = (
                            html
                            if ctype == "text/plain"
                            else trafilatura.extract(
                                html, include_comments=False, include_tables=True, favor_recall=True
                            )
                            or ""
                        )
                        source.text = text[:60000]
                        source.truncated = len(text) > 60000
                        source.access = (
                            Access.RETRIEVED if len(text.strip()) > 40 else Access.UNSUPPORTED
                        )
                        source.scope_confirmed = domain(url) == target_domain
                        source.kind = "official" if source.scope_confirmed else "third_party"
                        if domain(url) != target_domain and source.publisher != domain(source.url):
                            source.note = "Redirect needs identity review"
                        if domain(url) != target_domain:
                            source.note = (
                                "Third-party scope requires explicit domain/program mention"
                            )
                        parser = Links()
                        parser.feed(html)
                        links = []
                        for href in parser.hrefs:
                            try:
                                candidate = normalize_url(urljoin(url, href))
                                if domain(candidate) == target_domain and any(
                                    word in candidate.lower()
                                    for word in (
                                        "intern",
                                        "program",
                                        "terms",
                                        "faq",
                                        "fees",
                                        "about",
                                        "partner",
                                    )
                                ):
                                    links.append(candidate)
                            except ValueError:
                                pass
                        return source, list(dict.fromkeys(links))[:6]
                    raise ValueError("Redirect limit reached")
        except (TimeoutError, httpx.TimeoutException):
            source.access = Access.TIMEOUT
            source.note = "Fetch deadline reached"
        except (ValueError, OSError, httpx.HTTPError, httpcore.NetworkError):
            source.access = Access.BLOCKED
            source.note = "Fetch failed safety, format, or connection checks"
        return source, []
