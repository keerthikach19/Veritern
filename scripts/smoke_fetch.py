"""Explicit, non-billable public retrieval check; no company assessment."""

import asyncio

from veritern.config import Settings
from veritern.retrieval.safe import Fetcher


async def main():
    source, _ = await Fetcher(Settings(_env_file=None)).fetch("https://example.com/", "example.com")
    print({"access": source.access.value, "characters": len(source.text), "note": source.note})
    if source.access != "retrieved":
        raise SystemExit(1)


asyncio.run(main())
