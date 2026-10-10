# Contributing to Veritern

Start with the README, LIMITATIONS.md and docs/THREAT_MODEL.md. Run the offline tests and Ruff checks before proposing changes. A small, reviewable PR should explain the problem, behavior and verification.

## Evidence contributions

This repository accepts **fictional or appropriately licensed, consented, fully anonymized test fixtures**, not a public company blacklist. Never commit private offer letters, API keys, personal IDs, reviewer profiles, raw complaints or unverified accusations. Real-world evaluation needs separate review of consent, rights and scope before publication.

For a synthetic case, include reserved `.test`/`example.com` domains, provenance, quoted source text, explicit program/batch, known versus unknown fields, and expected rules. Keep near duplicates in one split. Do not tune against the heldout fixtures and keep claiming the original split is held out; bump the corpus version.

Useful first contributions:

- Add a negative example proving a disclosed optional fee does not trigger a contradiction.
- Add a mocked inaccessible-platform or changed-domain retrieval test.
- Improve accessible report wording without introducing a safety score.
- Document a supported host's persistence/egress checks with reproducible results.

Do not add scraping bypasses, silent provider/model fallback, autonomous outreach, local model downloads or public participant submissions to v1.
