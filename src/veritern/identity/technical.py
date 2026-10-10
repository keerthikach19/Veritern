"""Key-free connection observations. These never verify a business or employer."""

import asyncio
import ssl
from urllib.parse import urlsplit

import httpcore

from veritern.identity.resolve import normalize_url
from veritern.retrieval.safe import PublicBackend, UnsafeDestination, public_addresses
from veritern.schemas import Check


async def connection_checks(url: str, timeout: float = 8) -> list[Check]:
    parsed = urlsplit(normalize_url(url))
    host = parsed.hostname
    checks = []
    stream = None
    phase = "Public DNS"
    try:
        async with asyncio.timeout(timeout):
            addresses = await public_addresses(
                host, parsed.port or (443 if parsed.scheme == "https" else 80)
            )
            checks.append(
                Check(
                    name=phase,
                    state="resolved",
                    reason=f"{host} resolved to {len(addresses)} public network address(es). This establishes technical presence, not ownership or legitimacy.",
                )
            )
            phase = "HTTPS connection"
            if parsed.scheme != "https":
                checks.append(
                    Check(
                        name=phase,
                        state="not_attempted",
                        reason="The submitted URL uses HTTP. An encrypted connection was not tested.",
                    )
                )
                return checks
            # The backend validates and pins all addresses again at connection time.
            stream = await PublicBackend().connect_tcp(host, parsed.port or 443, timeout=timeout)
            stream = await stream.start_tls(
                ssl.create_default_context(), server_hostname=host, timeout=timeout
            )
            checks.append(
                Check(
                    name=phase,
                    state="resolved",
                    reason=f"A TLS handshake passed certificate and hostname validation for {host}. Encryption does not establish who runs the business or whether an offer is genuine.",
                )
            )
    except UnsafeDestination:
        checks.append(
            Check(
                name=phase,
                state="blocked",
                reason="Destination did not pass public-network safety checks.",
            )
        )
    except (TimeoutError, OSError, httpcore.NetworkError, httpcore.TimeoutException):
        checks.append(
            Check(
                name=phase,
                state="failed",
                reason="Connection could not be verified from this app. This can be a local network, DNS, server or certificate problem; it is not a fraud finding.",
            )
        )
    finally:
        if stream is not None:
            await stream.aclose()
    return checks
