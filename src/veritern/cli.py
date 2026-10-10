import argparse
import asyncio
import json
import shutil
import sys
import time
from pathlib import Path

from veritern.config import Settings
from veritern.demo import DEMOS, new_demo
from veritern.discovery.search import Search, SearchUnavailable
from veritern.schemas import Case
from veritern.storage.repository import Repository


async def live_doctor(settings):
    if settings.app_mode == "demo":
        print("Live doctor disabled in demo mode.")
        return False
    ok = True
    try:
        rows = await Search(settings).query('"example.com"')
        print(f"Search response: {len(rows)} leads (not a feasibility benchmark).")
    except SearchUnavailable as exc:
        print(str(exc))
        ok = False
    if not settings.groq_api_key.get_secret_value():
        print("Groq key absent: account/model smoke test not run.")
        return False
    import groq

    try:
        async with groq.AsyncGroq(
            api_key=settings.groq_api_key.get_secret_value(), max_retries=0, timeout=15
        ) as client:
            models = await client.models.list()
            if settings.groq_model not in {model.id for model in models.data}:
                print("Configured model not accessible.")
                return False
            response = await client.chat.completions.create(
                model=settings.groq_model,
                max_completion_tokens=128,
                messages=[{"role": "user", "content": "Return ok true."}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "doctor",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {"ok": {"type": "boolean"}},
                            "required": ["ok"],
                            "additionalProperties": False,
                        },
                    },
                },
            )
            valid = (
                response.choices[0].finish_reason == "stop"
                and json.loads(response.choices[0].message.content or "{}").get("ok") is True
            )
            print(f"Groq account/model structured-output check: {'passed' if valid else 'failed'}.")
            return valid and ok
    except Exception as exc:
        print(f"Groq check failed ({type(exc).__name__}); credentials/request content omitted.")
        return False


def evaluate(split: str):
    from veritern.rules import assess

    root = Path(__file__).resolve().parents[2] / "fixtures" / "synthetic"
    if not root.exists():
        root = Path(__file__).resolve().parent / "data" / "synthetic"
    rows = sorted((root / split).glob("*.json"))
    passed = 0
    failures = []
    started = time.perf_counter()
    for path in rows:
        data = json.loads(path.read_text(encoding="utf-8"))
        case = Case.model_validate(data["case"])
        actual = sorted({f.rule_id for f in assess(case)})
        if actual == sorted(data["expected_rules"]):
            passed += 1
        else:
            failures.append(
                {"fixture": path.name, "expected": data["expected_rules"], "actual": actual}
            )
    result = {
        "split": split,
        "passed": passed,
        "total": len(rows),
        "failures": failures,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "evaluation_type": "deterministic rule regression on pre-extracted synthetic facts; NOT model accuracy",
    }
    print(json.dumps(result, indent=2))
    return bool(rows) and passed == len(rows)


def main():
    parser = argparse.ArgumentParser(prog="veritern")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--offline", action="store_true")
    doctor.add_argument("--live", action="store_true")
    commands.add_parser("migrate")
    cleanup = commands.add_parser("cleanup")
    cleanup.add_argument("--expired-only", action="store_true", required=True)
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--split", choices=["development", "heldout"], default="heldout")
    commands.add_parser("prewarm-demo")
    args = parser.parse_args()
    try:
        settings = Settings()
    except ValueError:
        print("Invalid configuration; compare .env with .env.example. Values omitted.")
        raise SystemExit(2) from None
    if args.command == "doctor":
        print(f"Python: {sys.version.split()[0]}")
        print(
            f"Mode: {settings.app_mode}; search: {settings.search_backend}; configured: {settings.search_ready}"
        )
        print(f"Groq key present: {bool(settings.groq_api_key.get_secret_value())}")
        print(f"OCR executable available: {bool(shutil.which('tesseract'))}")
        Repository(settings.storage_dir).cleanup()
        for key in DEMOS:
            Case.model_validate(new_demo(key).model_dump())
        print("Offline schema, demo and SQLite checks: passed. No network calls.")
        if args.live and not asyncio.run(live_doctor(settings)):
            raise SystemExit(1)
    elif args.command == "migrate":
        Repository(settings.storage_dir).migrate()
        print("SQLite schema version 1 ready.")
    elif args.command == "cleanup":
        Repository(settings.storage_dir).cleanup()
        print("Expired unsaved cases and public caches cleared; no filesystem traversal.")
    elif args.command == "evaluate":
        if not evaluate(args.split):
            raise SystemExit(1)
    elif args.command == "prewarm-demo":
        repo = Repository(settings.storage_dir)
        for key in DEMOS:
            case = new_demo(key, "local-demo-library")
            case.saved = True
            repo.create(case)
        print("Six fictional cases saved. No live data or calls.")


if __name__ == "__main__":
    main()
