# Troubleshooting

**No Groq key:** put it in the local `.env`, never chat or shell history. Public evidence is still collected; the report says semantic analysis is unavailable. Demo works without any key.

**Model unavailable/401/403:** run `veritern doctor --live` explicitly. Check project access to `openai/gpt-oss-20b`; there is no model substitution. **429:** bounded retry obeys Retry-After within the case deadline; reduce activity and check your actual account limit. No free-tier entitlement is assumed.

**No search:** configure Serper or Brave credentials, your private SearXNG endpoint, or explicitly choose manual discovery. A search result is only a lead. **SearXNG 403:** enable JSON format and check instance authentication. Upstream engine blocks may still prevent useful discovery.

**Company name ambiguous:** select the correct candidate or enter its website. Matching a website scopes the investigation, not identity verification. **Reviews unavailable:** indexed snippets/links remain navigation leads; paste text or add a screenshot with consent.

**JS-only page, robots error, blocked platform:** access is shown as unsupported/blocked. No bypass, sign-in scraping or proxy rotation occurs. **Public PDF URL:** add the PDF locally; automated web retrieval accepts HTML/plain text only.

**Tesseract absent:** URL/text work continues. Paste image text or install the OS Tesseract executable and English data; no local LLM is needed. **PDF/image failure:** check size/page limits, encryption, file signature and OCR budget. An empty/uncertain OCR result must be reviewed.

**Input budget reached:** reduce source count or supply shorter relevant excerpts. The app returns a partial report rather than hiding missing analysis. **Case interrupted:** use Reassess/resume. Completed page caches and validated same-case extraction can be reused. Failed requests can have unknown provider usage.

**SQLite resets on Spaces:** use disposable synthetic mode or an approved persistent volume. Supabase/Turso are future adapters, not enabled integrations. Do not assume free persistent hosting.

**Windows uv permissions:** cached hardlinks can inherit inaccessible ACLs in managed sandboxes. Use an approved fresh project environment with `UV_PROJECT_ENVIRONMENT=.venv-local` and `uv sync --locked --link-mode copy`. Do not weaken global permissions. The verified environment path is recorded in PROGRESS.md.
