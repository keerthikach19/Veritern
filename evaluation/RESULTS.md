# Measured verification — 2026-10-10

Environment: Windows, Python 3.13.7, copied project environment `.venv-local`. Veritern 0.1.0; rules 1.0; prompt extract-v1; Groq model configured as openai/gpt-oss-20b, not account-tested.

## Offline checks

- Initial suite: 120 passed; one UI path failure and 31 Windows asyncio fixture errors. The network-denial fixture had blocked the stdlib loopback socketpair used by Windows asyncio; it now permits only that specific stdlib operation, while app connections remain blocked.
- Next run: 146 passed and six retrieval stream failures. Fixed bounded response reading to support both streaming and mock preloaded responses, while refusing compression.
- Subsequent complete run: 154 passed; after document-only flow regression: 155 passed. **Final expanded suite: 159 passed in 71.87 seconds**, including text-PDF/OCR skip, PDF page limit, image pixel cap, missing OCR and subprocess timeout checks.
- Ruff lint and format checks passed. No real provider calls occur in the offline suite.
- Offline doctor, SQLite migration and expired-only cleanup passed.
- Streamlit AppTest verified home → fictional initial report → standardized task sheet → later fee contradiction → case deletion.
- Browser inspection verified the actual running home and fee-contradiction report. Screenshots are under docs/screenshots/.

## Frozen rule corpus

| Split | Matching expected rule sets | Measured run time |
|---|---:|---:|
| Development, corpus v2 | 30 / 30 | 0.0620 s |
| Heldout, corpus v2 | 30 / 30 | 0.0338 s |

There are 20 scenario families, with three variants each. Corpus v2 groups the shared free-certificate counterfactual templates in development; this corrects a template overlap in the original split without changing evidence or rules. Families and variants stay within one split; the manifest hashes freeze files. All 61 corpus/provenance/partition tests passed after regrouping. This is a **deterministic rule regression using pre-extracted fictional facts**, not extraction accuracy. The same builder authored code and fixtures; zero independent human reviewers. No statistical accuracy claim is justified.

Every fixture passed schema/provenance validation. Expected rule sets matched; invalid quotation/reference cases are tested for rejection. Tests explicitly preserve unknowns, separate program/batch/benefit mismatches, prohibit snippet/OCR-ambiguous material findings, and retain opposing evidence. The suite is not a claim that every semantic scenario in PLAN.md has been validated with real model output.

## Live observations

One non-billable HTTPS retrieval of `https://example.com/` succeeded through the connection-pinned transport and returned 156 extracted characters. An earlier sandbox-limited attempt could not establish robots access; the approved network retry succeeded. This verifies a real TCP/TLS retrieval path on this host, **not search feasibility or company coverage**.

Groq/search keys were absent. No model inference or commercial search quota was consumed during verification. The ten-company/15–20-program discovery study was not run. Entity mismatch rate, source usefulness, extraction precision/recall, material-finding precision, p50/p95 live latency and real costs are **unmeasured**. There is no consented real-world evaluation set or two-human review.

## Packaging and licensing

A wheel and source archive built successfully. The installed development environment measured 386.6 MiB of logical file sizes; this excludes the separately installed Tesseract executable and an unused failed first environment. No local LLM/embedding/GPU package was installed.

The wheel was unpacked into an isolated package directory and imported from there using existing environment dependencies; its bundled heldout evaluator passed 30/30. This checks installed-layout packaging, not a fresh operating-system install. A generated fictional PNG was also processed by the actual installed Tesseract: it extracted the expected `50` amount and marked critical-field review required.

The generated inventory records 79 third-party distributions and 110 bundled notice files. All distributions expose license metadata; dnspython, pypdfium2 and Streamlit had no individually exposed bundled notice file in the inspected wheel inventory. This remains a target-platform distribution-review item, not a completed legal audit. PDFium binary notices found in the distribution are preserved where exposed.

The OCI deployment has not been built/run on a hosting provider. Authentication, persistent disk, egress and hosted retention behavior remain unverified. Public anonymous deployment is outside this release.
# Follow-up validation — 10 October 2026

- Full offline suite after website/references changes: **199 passed in 11.27 seconds**. Ruff check and formatting passed.
- Five provided-reference records validate; URL routing, lookalike rejection, ambiguous phrase matching, exact quotation validation, report provenance and the Streamlit reference/compare/model-card flow are covered. These are not five authenticated company investigations.
- Actual browser check: entering `https://internpe.in/` with the reference option enabled opened its supplied-text review, with unperformed OCR/AI/authentication disclosed.
- Separate network smoke: the normal no-key pipeline fetched four InternPE HTML pages in **8.29 seconds**, passed DNS/TLS checks and made **zero model calls**. This was a retrieval/assembly check, not an authenticity determination. The original failure was reproduced under restricted networking and did not reproduce with normal outbound access.
- Built a wheel; isolated installed-layout verification loaded all five bundled reference records and passed 30/30 held-out deterministic rule fixtures.
- Live commercial search, Groq inference, model-quality evaluation, original-image OCR for the five references, and registry/issuer authentication remain unperformed.
