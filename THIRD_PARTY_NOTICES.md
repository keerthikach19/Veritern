# Third-party software and services

Original Veritern code is licensed under Apache-2.0 (LICENSE). This does not relicense dependencies, model weights, or retrieved evidence.

`dependency-licenses.json` records installed distribution versions and actual license metadata. `docs/licenses/` preserves license/NOTICE files shipped by those distributions, including bundled binary notices when provided. This inventory includes development tools and platform-specific installed packages; the cross-platform lockfile can select other wheels. Metadata is evidence, not a legal compatibility opinion. Review UNKNOWN/missing metadata and target-platform binary notices before distribution.

The runtime includes Streamlit, Pydantic, HTTPX/httpcore, Groq SDK, Trafilatura, pypdf, pypdfium2/PDFium, Pillow, pytesseract, tldextract and their dependencies. PDFium/image processing libraries may carry third-party binary notices distinct from the Python wrapper. Tesseract is a separately installed system executable, not bundled by this repository; preserve its installed notices too.

The selected `openai/gpt-oss-20b` model has its own [model card and license](https://huggingface.co/openai/gpt-oss-20b). No weights are downloaded or redistributed here. Groq inference is a proprietary hosted service; Serper/Brave/search upstreams and cloud hosting have their own terms and quotas.

Optional SearXNG runs separately and is AGPL licensed. Preserve upstream notices and review corresponding-source obligations if modifying/serving it. No SearXNG code or container image is vendored here.

Publicly accessible company pages, reviews and uploaded documents are not automatically open-licensed. The public repository includes author-created fictional fixtures only. Private reports are not a redistribution license for third-party content.
