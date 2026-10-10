# Architecture

Streamlit calls a Python domain layer. A single bounded worker runs an asyncio investigation; only the UI thread uses Streamlit. SQLite tracks owner-scoped cases, idempotent jobs and a public page cache. Every source has a stable ID, retrieval time, nullable event/publication dates, kind, access state and content hash.

Flow: explicit website confirmation or search candidate selection → neutral domain queries → robots-aware public fetching → scoped source eligibility → one Groq extraction batch → exact-quote/amount/date/condition validation → deterministic dimension-specific rules → versioned reports.

Serper is the default; Brave, operator-hosted SearXNG and manual discovery are explicit alternatives. Commercial APIs are authorized by the user's amendment to PLAN.md. No automatic provider fallback. Indexed snippets are displayed separately and cannot trigger findings. Reddit, LinkedIn and Glassdoor direct access is not attempted.

HTTPX 0.28.1/httpcore 1.0.9 are pinned because the safe transport sets the pool network backend. Every TCP connection resolves all addresses, rejects nonpublic answers and connects to a validated numeric literal. httpcore retains the original hostname for TLS certificate validation and SNI. Redirects repeat URL, robots and connection checks. Environment proxies are disabled. Unrequested compression is refused, response bytes are bounded, and the whole case has a deadline.

Evidence is explicitly scoped. First-party pages establish advertised claims, not delivery. Third-party content must mention the exact target domain or a specific supplied program. Company-name candidates always require selection. Automated authority verification is deliberately unavailable; official denials and partner confirmations cannot be promoted to authoritative status by the model.

Private files go through a timed subprocess, format signatures and limits. Text-only PDFs avoid OCR. OCR-derived critical fields require user review. Raw bytes are not persisted; edited redacted text is stored only after scope/review/consent checks. A Windows subprocess is not a complete OS sandbox.

Public page cache: URL hash and extraction version, configured TTL. Extraction cache: content/source IDs + model + prompt version within the owning case only. Job key: case + evidence revision + pipeline version. Cancel flags are checked before work and provider calls; in-flight calls may finish. Deleted cases become content-free tombstones before cleanup, so old workers cannot restore them. Interrupted jobs become partial on startup. Saved histories can be reopened only through the local single-user library.

Assessment history retains old spans; adding evidence creates new assessments. Exports omit raw source text, owner IDs and original uploads. Unknowns stay visible; no overall scam score exists. Rule-based regressions exercise pre-extracted facts, not hosted-model extraction accuracy.
