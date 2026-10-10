"""Explicit, non-billable public retrieval check; no company assessment."""

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from veritern.config import Settings
from veritern.identity import domain, normalize_url
from veritern.pipeline.runner import Runner
from veritern.retrieval.safe import Fetcher
from veritern.schemas import Case, Entity
from veritern.storage.repository import Repository


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="https://example.com/")
    parser.add_argument(
        "--basic-review",
        action="store_true",
        help="Run no-key website review in temporary local storage",
    )
    args = parser.parse_args()
    url = normalize_url(args.url)
    if args.basic_review:
        Path("private_data").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="smoke-", dir="private_data") as folder:
            settings = Settings(
                _env_file=None,
                storage_dir=Path(folder),
                search_backend="manual",
                groq_api_key="",
                app_mode="live",
            )
            repo = Repository(settings.storage_dir)
            case = Case(
                owner="smoke",
                original_input=url,
                entity=Entity(name=domain(url), domain=domain(url)),
                mode="manual",
            )
            repo.create(case)
            runner = Runner(settings, repo)
            repo.claim_job("smoke", case.id, case.owner)
            try:
                await runner.run("smoke", case.id, case.owner)
                result = repo.get(case.id, case.owner)
                report = result.assessments[-1]
                print(
                    json.dumps(
                        {
                            "headline": report.headline,
                            "sources": [
                                {
                                    "url": s.url,
                                    "access": s.access,
                                    "characters": len(s.text),
                                    "note": s.note,
                                }
                                for s in result.sources
                            ],
                            "topics": [
                                {"title": t.title, "state": t.state, "excerpts": len(t.span_ids)}
                                for t in report.website_topics
                            ],
                            "checks": [
                                c.model_dump()
                                for c in report.checks
                                if c.name
                                in (
                                    "Public DNS",
                                    "HTTPS connection",
                                    "Automated discovery",
                                    "Structured extraction",
                                )
                            ],
                            "seconds": report.usage.elapsed_seconds,
                            "model_calls": report.usage.calls,
                        },
                        indent=2,
                    )
                )
                if not any(s.access == "retrieved" for s in result.sources):
                    raise SystemExit(1)
            finally:
                runner.executor.shutdown(wait=True)
        return
    source, _ = await Fetcher(Settings(_env_file=None, app_mode="live")).fetch(url, domain(url))
    print({"access": source.access.value, "characters": len(source.text), "note": source.note})
    if source.access != "retrieved":
        raise SystemExit(1)


asyncio.run(main())
