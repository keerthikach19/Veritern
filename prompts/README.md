# Prompt registry

`extract-v1` is the `PROMPT` constant and strict `Extraction` schema in `src/veritern/llm/client.py`. Keeping the executable prompt in the installed module avoids a missing external-file failure after packaging. Change its version and invalidate extraction fingerprints whenever semantics change.

The model has no tools. All sources are untrusted; exact quotations and typed fields are checked locally. Strict JSON is not proof of semantic truth. No free-form verdict fallback exists. English only. Unsupported date formats remain unknown rather than silently inferred.
