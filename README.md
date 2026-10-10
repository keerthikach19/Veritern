# Veritern

**Check the evidence before you join.**

Veritern is a local internship due-diligence application. Start with a company website, choose a company-name search candidate, or review an offer letter/message. Compare advertised promises with scoped evidence, inspect exact quotations, and see what could not be checked.

It is **not a scam detector**. There are no scam percentages, criminal labels, or verified-safe badges. Identity, experience, marketing/partnerships, and fees/compensation remain separate.

## What works

- Company URL or name entry with explicit website confirmation/candidate selection.
- Serper (default), Brave, optional privately operated SearXNG, and manual discovery adapters; no hidden fallback.
- Concurrent public HTML/text retrieval with robots handling, validated connection addresses, redirect checks, bounded sizes/deadlines, and public page caching.
- PDF, PNG/JPEG, TXT, EML and pasted evidence; text-first PDF parsing and optional English Tesseract OCR.
- Document-only local review of payment wording, sensitive requests and sender-domain differences without API keys. These are transparent review cues, not complete semantic analysis.
- Editable redaction preview, critical-field review, and optional explicit consent before private text goes to Groq.
- Batched Groq extraction using `openai/gpt-oss-20b`, strict schema and local quotation/scope/amount/date validation. No local model download.
- Deterministic promise/fee/compensation/mentorship/partnership rules, opposing evidence, dates and separate unknowns.
- Background progress, cancellation, idempotent jobs, case-scoped extraction reuse, persistent usage reservations and partial reports.
- Assessment history, adding later evidence/corrections, private Markdown/JSON export, local saved library and deletion.
- Six fictional interactive examples and 60 frozen synthetic rule-regression fixtures.

**Live acceptance is not yet verified:** no Groq/search credentials were supplied during the build. Offline tests are not a claim about live search coverage or model accuracy. See [evaluation results](evaluation/RESULTS.md), [limitations](LIMITATIONS.md), and [implementation status](PROGRESS.md).

[View the verified fictional report screenshot](docs/screenshots/demo-report.png).

## Run on Windows

Python 3.13.7 was used for this build; the project supports Python 3.11–3.13. Install Python and [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed. In PowerShell, from this folder:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-local'
uv sync --locked --link-mode copy
Copy-Item .env.example .env
.\.venv-local\Scripts\python.exe -m veritern.cli doctor --offline
.\.venv-local\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open the localhost URL printed by Streamlit. Choose **Try a fictional example** to use the app without credentials. `scripts/run.ps1 -Demo` is also available. This workspace uses `.venv-local` because the first cache-hardlinked `.venv` hit managed Windows permission errors; no global permissions were changed.

## macOS / Linux

These instructions are supplied but were not executed on those operating systems during this build:

```bash
uv sync --locked
cp .env.example .env
uv run veritern doctor --offline
uv run streamlit run app.py --server.address 127.0.0.1
```

Pip fallback: create/activate a project venv, then `python -m pip install -r requirements.txt` and `python -m pip install --no-deps .`. The exported requirements pin runtime dependencies. Use uv's lockfile for development/test dependencies.

## Configure live research

Edit `.env` privately. Never put keys in chat, screenshots, source files or command history.

1. Set `GROQ_API_KEY` from your own Groq account. The only configured model is `openai/gpt-oss-20b`; account capability must pass the live doctor.
2. Set `SERPER_API_KEY` for the default provider, or choose `SEARCH_BACKEND=brave` with `BRAVE_API_KEY`.
3. Alternatively configure your own SearXNG endpoint or set `SEARCH_BACKEND=manual`. API trials, quotas and hosting are account-dependent; no free allowance is assumed and no billing is activated by this app.
4. Run `uv run veritern doctor --live` explicitly. It makes a small search request and one bounded model request, which may count toward provider quotas. It prints no keys or prompts.
5. Enter the intended website and program. Inspect source scope and quotes before relying on the report.

`APP_MODE=demo` blocks live research/model calls. Missing keys never silently turn live cases into fictional results. Reddit, LinkedIn and Glassdoor direct access remains **not checked**; search snippets are leads only. Add consented text/screenshots when useful.

Groq hosting and commercial search are proprietary external services; the application and selected model weights are openly licensed. No ChatGPT/OpenAI API key, GPU, Torch, Transformers, vector database or local LLM is required. See [Groq structured outputs](https://console.groq.com/docs/structured-outputs) and account data controls before approving private text.

## OCR and data

Tesseract is optional. Install its executable and English language data through your trusted OS package route if image/scanned-PDF OCR is needed. Without it, URL/text investigations continue and the UI requests pasted text. `packages.txt` records server package names. Original uploads are not stored by the repository; approved excerpts are stored locally.

SQLite is unencrypted and intended for one trusted local user. Unsaved cases expire after 24 hours, with cleanup when the app next runs. Saved history persists until deletion. Cloud disks may be ephemeral: set `EPHEMERAL_STORAGE=true` unless persistence is verified. Supabase/Turso is not implemented. See [privacy](docs/PRIVACY.md) and [protected deployment](deploy/README.md).

## Checks and commands

With the Windows environment variable above set, the same uv commands work on Windows:

```text
uv run veritern doctor --offline
uv run veritern migrate
uv run pytest -m "not live" -q
uv run veritern evaluate --split development
uv run veritern evaluate --split heldout
uv run veritern cleanup --expired-only
uv run veritern prewarm-demo
uv run ruff check .
uv run ruff format --check .
```

`prewarm-demo` saves six explicitly fictional examples, without provider calls. `evaluate` tests rules against pre-extracted synthetic facts; it does not run Groq or measure extraction precision/recall. Frozen scenario families remain in a single split. The repository CI runs offline checks; remote CI status is separate from local verification.

## Project map

- `src/veritern/`: schemas, ingestion, search, safe retrieval, model adapter, local/rule analysis, storage, pipeline, reports and Streamlit UI.
- `fixtures/synthetic/`: shareable fictional evidence and expected rules; no real participant records.
- `tests/`: unit, mocked integration, security and UI behavior tests.
- `docs/`: architecture, privacy, threat model, troubleshooting and [two-minute demo](docs/DEMO.md).
- `dependency-licenses.json`, `docs/licenses/`: installed dependency metadata and bundled notices.
- `PLAN.md`: original handoff, preserved unchanged. Its former OfferCheck name and SearXNG-first choice are superseded by the user's Veritern naming and search-provider instructions.

Original application code is Apache-2.0. Third-party code, model weights and website evidence retain their own licenses/rights. Read [contribution guidance](CONTRIBUTING.md) before proposing evidence fixtures.
