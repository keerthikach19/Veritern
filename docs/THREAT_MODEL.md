# Threat model and release boundary

Untrusted inputs include names, URLs, website text, snippets, uploads, email headers and model output. Risks include wrong-company merges, forged reviews, prompt injection, SSRF, malicious files, data leakage, abusive provider spend and overconfident allegations.

Implemented controls: explicit target confirmation; offline PSL snapshot; connection-time public IP validation; TLS hostname preservation; redirect revalidation; no proxies, cookies, scripts or form submission; robots policy; byte/time/concurrency caps; strict schemas; exact quote and semantic field checks; snippet exclusion; private consent; owner-scoped persistence; tombstones; bounded worker/model budgets; no model tools; escaped/plain source rendering and exports; zero-call demo mode.

Residual limitations:

- Parser/OCR subprocesses have timeout and page/pixel limits, but Windows resource/network isolation is incomplete. Protected mode therefore refuses private uploads. Malicious native parser vulnerabilities require OS/container isolation and patch maintenance.
- DNS pinning and mocked safety tests are necessary, not a completed independent security audit. No public deployment is approved by passing synthetic tests.
- A valid quotation can still be forged or semantically misclassified. Amount/date guards are conservative; non-ISO dates are unknown. A single model can omit conditions. Model precision/recall awaits live, consented evaluation.
- Exact-copy deduplication cannot establish independent authorship or all paraphrase/repost chains. Conflicting accounts are retained; automatic strong corroboration is not assigned.
- Local saved-library access trusts the OS user, not a browser account. Use authenticated ingress for protected demo and keep uploads off. Public tenant isolation/abuse protection are a future release.
- Cache data may age within its TTL. Reports label retrieval time/cache use and do not treat it as publication date.
- Endpoints, host egress, model availability and provider quotas require actual account smoke tests.
