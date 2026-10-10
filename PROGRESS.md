# Veritern implementation progress

Original PLAN.md preserved unchanged. User amendments select Veritern naming, Serper/Brave-first search, optional SearXNG, bounded asynchronous work, explicit unavailable platforms and deferred assignment similarity. The follow-up suggestions added document-first local cues and open-source contribution/limitations documentation.

| Phase | Status and evidence |
|---|---|
| 0 — environment | Complete locally. Windows/Python 3.13.7/uv/Tesseract detected. Fresh `.venv-local` installed with copied packages after the first `.venv` had managed cache-hardlink permission errors. Offline doctor passes. |
| 1 — schemas/fixtures/storage | Implemented and tested. Strict records, exact spans, migrations, owner checks, tombstones, version history, six interactive demos, 60 frozen fictional regression cases. Broader relationship/experience-record design is represented by typed claims rather than a separate full ontology. |
| 2 — discovery | Four adapters and safe fetch implemented; mocked adapter/security tests pass. Real example.com TCP/TLS retrieval succeeds. Company discovery feasibility remains unmeasured without keys/reference sample. |
| 3 — ingestion/privacy | PDF/image/EML/TXT parsing, OCR limits, timed subprocess, editable redaction, critical-field review and cloud consent implemented. Raw uploads not persisted. OS-level parser isolation remains incomplete on Windows; protected uploads disabled. |
| 4 — Groq | Strict schema, exact quotation/scope/amount/date checks, one batched request, retry/deadline budgets, persisted reservations and private case extraction reuse implemented and mocked. Actual account capability/extraction accuracy unverified. |
| 5 — rules | Fee/compensation/experience/partnership/authority/conditions rules and local document cues implemented. 60/60 frozen rule cases pass. Exact-copy grouping only; paraphrase independence, automated RDAP/registry/partner authority verification deferred. |
| 6 — UI | Website/name/doc-only entry, selection, progress/cancel, evidence/report/coverage/history, add/correct, export/delete and demos implemented. AppTest and actual browser inspection pass. Live URL-only acceptance remains gated on providers. |
| 7 — evaluation/security | Offline suite and lint pass; synthetic rule metrics recorded. No real-world accuracy, full security audit or independent human validation claimed. |
| 8 — package/protected demo | Lockfile, exported requirements, wheel/source build, license inventory, container instructions, CI and runbooks prepared. Host authentication, persistence and deployment not verified or published. |

## Verified commands

Use `.venv-local\Scripts\python.exe` below on this Windows checkout. Source setup uses `$env:UV_PROJECT_ENVIRONMENT='.venv-local'; uv sync --locked --link-mode copy`.

- `python -m pytest -m "not live" -q --tb=short` — **159 passed in 71.87 seconds**, zero failures/warnings in the final expanded run.
- `python -m veritern.cli doctor --offline` — passed; keys absent, Tesseract present.
- `python -m veritern.cli migrate` — schema 1 ready.
- `python -m veritern.cli cleanup --expired-only` — completed.
- `python -m veritern.cli evaluate --split development` — 30/30.
- `python -m veritern.cli evaluate --split heldout` — 30/30.
- Corpus v2 groups shared fee templates in one split; all 61 frozen-corpus tests passed after regrouping. No evidence/rule changes were made by that regrouping.
- `ruff check .` and `ruff format --check .` — passed.
- `python scripts/smoke_fetch.py` — approved external-network retry retrieved 156 characters from example.com.
- `python scripts/dependency_report.py` — 79 distributions, 110 notices.
- `python scripts/check_public_files.py` — no tracked private paths/obvious credential tokens at the checked revision.
- `uv build --out-dir dist` — wheel and source archive built.
- `python scripts/verify_wheel.py` — installed-layout import and bundled heldout fixtures passed 30/30 using existing dependencies.
- Actual Tesseract smoke test on a generated fictional PNG — expected amount extracted; critical-field review required.
- `python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true` — running UI verified in browser.

## Remaining operator actions

Enter Groq and the selected search provider key privately in `.env`; run the explicitly network-enabled live doctor. Supply/choose a reviewed discovery benchmark before asserting live coverage. Choose protected hosting and verified persistent storage before deployment. No billing, public evidence platform or remote database was activated.

Implementation commit: `b9b4293`. Reliability, setup, packaging and CI commit: `2d5d512`. Documentation/license handoff commit: `7e18118`. These were pushed to https://github.com/keerthikach19/Veritern; `main` tracks `origin/main`. A final packaging-check fix uses fresh extraction directories, and the final wheel's bundled evaluator passed 30/30 again.
