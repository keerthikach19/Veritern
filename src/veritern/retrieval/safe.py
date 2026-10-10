import asyncio
import ipaddress
import socket
import zlib
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


class RobotsUnavailable(Exception):
    pass


def redirect_url(current: str, location: str) -> str:
    try:
        return normalize_url(urljoin(current, location))
    except ValueError as exc:
        raise UnsafeDestination("Unsafe redirect destination") from exc


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
            for i, address in enumerate(addresses):
                try:
                    return await self.backend.connect_tcp(
                        address,
                        port,
                        (timeout or 12) / len(addresses),
                        local_address,
                        socket_options,
                    )
                except (httpcore.ConnectError, httpcore.ConnectTimeout, OSError):
                    if i == len(addresses) - 1:
                        raise

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


class CompanyText(HTMLParser):
    """Preserve footer/contact text that article extractors intentionally discard."""

    ignored_tags = {"head", "script", "style", "noscript", "template", "svg", "nav", "form"}
    block_tags = {
        "p",
        "div",
        "section",
        "article",
        "footer",
        "li",
        "br",
        "h1",
        "h2",
        "h3",
        "h4",
        "tr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.ignored_tags:
            self.ignored.append(tag)
        if not self.ignored and tag in self.block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.ignored:
            self.ignored.remove(tag)
        if not self.ignored and tag in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)

    def text(self):
        return "\n".join(
            line for raw in "".join(self.parts).splitlines() if (line := " ".join(raw.split()))
        )


class Fetcher:
    def __init__(self, settings: Settings, transport=None):
        self.settings = settings
        self.transport = transport
        self.host_locks: dict[str, asyncio.Lock] = {}
        self.robots: dict[str, RobotFileParser | bool | str] = {}

    async def _read(self, client, url, max_bytes):
        async with client.stream("GET", url) as response:
            encoding = response.headers.get("content-encoding", "identity").lower()
            if encoding not in ("identity", "", "gzip"):
                raise ValueError("Server used an unsupported content encoding")
            if int(response.headers.get("content-length", "0")) > max_bytes:
                raise ValueError("Response exceeds byte budget")
            data = bytearray()
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
            # Bound decompression itself, not just its output after allocation.
            wire_bytes = 0
            chunks = (
                response.aiter_raw() if not response.is_stream_consumed else response.aiter_bytes()
            )
            if response.is_stream_consumed:
                decoder = None  # Mock/preloaded responses have already been decoded by HTTPX.
            async for chunk in chunks:
                wire_bytes += len(chunk)
                if wire_bytes > max_bytes:
                    raise ValueError("Response exceeds byte budget")
                data.extend(
                    decoder.decompress(chunk, max_bytes - len(data) + 1) if decoder else chunk
                )
                if len(data) > max_bytes:
                    raise ValueError("Response exceeds byte budget")
            if decoder and (not decoder.eof or decoder.unused_data):
                raise ValueError("Incomplete or concatenated gzip response")
            return response, bytes(data)

    async def _allowed(self, client, url):
        origin = str(httpx.URL(url).copy_with(path="/robots.txt", query=None, fragment=None))
        if origin not in self.robots:
            try:
                current = origin
                for hop in range(6):
                    response, raw = await self._read(client, current, 512000)
                    if not response.is_redirect:
                        break
                    if hop == 5 or not response.headers.get("location"):
                        raise RobotsUnavailable("Robots policy redirect limit reached")
                    current = redirect_url(current, response.headers["location"])
                    if domain(current) in RESTRICTED:
                        raise RobotsUnavailable("Robots policy redirected to a restricted platform")
                if response.status_code in (404, 410):
                    self.robots[origin] = True
                elif response.status_code != 200:
                    raise RobotsUnavailable(f"Robots policy returned HTTP {response.status_code}")
                else:
                    if "<html" in raw[:1024].decode("utf-8", errors="replace").lower():
                        raise RobotsUnavailable("Robots policy returned HTML instead of rules")
                    parser = RobotFileParser()
                    parser.parse(raw.decode("utf-8", errors="replace").splitlines())
                    self.robots[origin] = parser
            except UnsafeDestination:
                raise
            except (RobotsUnavailable, ValueError, zlib.error) as exc:
                self.robots[origin] = str(exc)
            except (httpx.HTTPError, httpcore.NetworkError, OSError):
                self.robots[origin] = (
                    "Could not connect to read robots.txt. Check this app's internet access; "
                    "this is not a website blocking verdict"
                )
        policy = self.robots[origin]
        if isinstance(policy, str):
            raise RobotsUnavailable(policy)
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
                                source.note = "The site's robots.txt explicitly disallows this path for Veritern"
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
                            url = redirect_url(url, response.headers.get("location", ""))
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
                        if ctype != "text/plain" and domain(url) == target_domain:
                            # Article extraction often drops company identity/contact footers.
                            # Keep the site's cleaned body text for a company review instead.
                            body = CompanyText()
                            body.feed(html)
                            text = body.text() or text
                        source.text = text[:60000]
                        source.truncated = len(text) > 60000
                        source.access = (
                            Access.RETRIEVED if len(text.strip()) > 40 else Access.UNSUPPORTED
                        )
                        source.scope_confirmed = domain(url) == target_domain
                        source.kind = "official" if source.scope_confirmed else "third_party"
                        source.note = "Public page retrieved; website statements are self-published and unverified"
                        if source.access == Access.UNSUPPORTED:
                            source.note = "No readable page text found; the page may require JavaScript or be an access challenge"
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
                                        "contact",
                                        "refund",
                                        "pricing",
                                    )
                                ):
                                    links.append(candidate)
                            except ValueError:
                                pass
                        links = list(dict.fromkeys(links))
                        links.sort(
                            key=lambda item: (
                                not any(
                                    word in item.lower()
                                    for word in (
                                        "about",
                                        "contact",
                                        "terms",
                                        "fee",
                                        "refund",
                                        "faq",
                                    )
                                )
                            )
                        )
                        return source, links[:6]
                    raise ValueError("Redirect limit reached")
        except (TimeoutError, httpx.TimeoutException):
            source.access = Access.TIMEOUT
            source.note = "Fetch deadline reached"
        except RobotsUnavailable as exc:
            source.access = Access.ROBOTS_UNAVAILABLE
            source.note = (
                str(exc)
                + ". Page fetching paused until the policy can be read. No inference about legitimacy."
            )
        except UnsafeDestination:
            source.access = Access.BLOCKED
            source.note = "Destination rejected by public-network safety checks"
        except (ValueError, zlib.error) as exc:
            source.access = Access.UNSUPPORTED
            source.note = str(exc)
        except (OSError, httpx.HTTPError, httpcore.NetworkError):
            source.access = Access.NETWORK
            source.note = "Connection failed from this app. Check internet access, DNS and TLS; the site was not verified or judged blocked"
        return source, []
