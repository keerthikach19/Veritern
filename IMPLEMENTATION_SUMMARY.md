# Veritern — build handoff

## Delivered

Built a runnable Python/Streamlit v1 from the original PLAN.md, preserved that file, and adopted the user's final project name **Veritern** across the package, CLI, UI, exports and deployment materials.

### Entry and identity

Website-only entry works without uploads. Company-name search returns candidates that require explicit selection. The confirmed website scopes the case rather than proving identity. Optional program names help reject unrelated content. A document-only case can start without website/API credentials.

### Research

Serper is the default adapter; Brave, private SearXNG and manual discovery are selectable. Neutral domain-based query families cover experience, terms, fees, payment and reviews. Snippets remain labeled leads. LinkedIn, Glassdoor and Reddit direct access is explicitly not checked. Public fetching uses concurrency limits, robots rules, page/domain/byte limits, timeout/deadline controls, redirect validation and a TCP backend that connects to validated public IPs while retaining TLS hostname checks. No scripts, login bypass, cookies, forms or proxy rotation.

### Evidence and privacy

PDF/PNG/JPEG/TXT/EML and pasted text are supported. PDFs use embedded text first; sparse pages/images can use bounded English OCR. Parsing runs in a timed subprocess. Raw uploads are not stored by the repository. Users edit a redaction preview and review critical fields before adding evidence. Cloud consent is optional and specific; only approved private text can reach Groq. Local document cues still work without it.

### Extraction and assessment

One approved Groq model, strict schema and batched selected passages. Local validation rejects unknown citations, absent quotes, conflicting program scope, unsupported amounts/dates/conditions and ambiguous OCR. There is no model/tool execution or free-form verdict fallback. Persistent token/call reservations cover retries and cancelled requests, and same-case extraction fingerprints avoid redundant calls.

Rules distinguish optional disclosed charges, unknown disclosure, explicit later fee contradictions, guaranteed versus conditional compensation, reported overdue payment, standardized educational projects, mentorship discrepancies, partnership scope and recruitment/promotion conditions. Four dimensions stay separate. Contrary accounts and reported resolutions remain visible. Local document cues flag payment wording, sensitive requests and sender-domain differences as questions, not authenticated wrongdoing.

### Workflow and reports

The UI shows background progress and cancellation, reports partial work honestly, and separates findings from the check ledger. Users can inspect exact quotations, dates, attribution, scope and access state; add later evidence/corrections; compare assessment versions; download redacted Markdown/JSON; save local history; and delete cases. SQLite owner checks, per-thread connections, recovery state and deletion tombstones prevent deleted records being recreated by old workers.

### Demo, tests and distribution

Six fictional examples are ready without keys. The Cedar Learning flow demonstrates initial unknowns, a task sheet and a later ₹50 request. Sixty frozen fictional cases have explicit expected rule sets and family-separated development/heldout splits. GitHub CI, Apache-2.0 license, dependency lockfile/runtime export, dependency-license inventory, retained notices, container recipe, SearXNG settings example, OCR package list and setup/deployment/privacy/threat/troubleshooting/demo/contribution documentation are included.

## Verified locally

- **159 offline tests passed**, including mocked providers, rules, provenance, SSRF, privacy, parsing limits, storage, jobs and Streamlit interactions.
- **30/30 development and 30/30 heldout rule-regression cases passed.** These use pre-extracted synthetic facts and do not measure model accuracy.
- Ruff lint/format, offline doctor, migration and expiry cleanup passed.
- Real HTTPS example.com fetch through the safe transport succeeded, extracting 156 characters.
- Running browser UI and the later-fee demo were inspected; screenshots are provided.
- Wheel/source archive build succeeded. Installed environment measured 386.6 MiB, with no local LLM or GPU libraries.
- Inventory contains 79 third-party distributions and 110 bundled notices. Missing individually exposed notices in three wheel inventories remain a distribution-review item.

## What remains partial or blocked

Groq and search keys were not supplied, so actual account access, real-company discovery, live extraction quality, provider latency/quotas and costs remain unverified. The planned multi-company feasibility study and independent human review were not performed. Enter keys privately in `.env` and run the live doctor before claiming live research acceptance.

The runtime does not verify document authenticity, email signatures, registry authority, all review origins, hidden unpublished experiences or future payment. Exact copied content is grouped; paraphrase/independence verification is not implemented. RDAP/Wayback/registry automation, similarity analysis, voice, multilingual claims and public evidence submissions remain deferred. The parser lacks a full OS sandbox on Windows, so protected deployments disable private uploads.

SQLite is local and unencrypted. Ephemeral hosting may lose history; Supabase/Turso is not implemented. Protected hosting, authentication, persistence and container operation are prepared/documented but not deployed or verified. This is a tested local v1, not a production-security or real-world-accuracy certification.

## Run

In this checkout:

```powershell
.\.venv-local\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

See README.md for installation, key setup and cross-platform commands. Use a fictional example first. The project is pushed to `https://github.com/keerthikach19/Veritern`, with local `main` tracking `origin/main`.
