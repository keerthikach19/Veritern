# Protected demonstration

Default container mode is synthetic and private uploads are disabled. The image is prepared, not deployed or runtime-verified. Place it behind platform authentication and HTTPS before exposing it. Public anonymous multi-user operation is out of scope.

1. Review the Python base image and pin its registry digest for your platform before release; the supplied version tag is not an immutable digest.
2. Build from the repository root: `podman build -f deploy/Containerfile -t veritern .`
3. Run behind your authenticated ingress with one instance: `podman run --rm -p 127.0.0.1:7860:7860 veritern`.
4. For live research, inject `APP_MODE=live`, selected search key and Groq key through host secrets. Never bake `.env` into an image. Do not activate paid billing automatically.
5. Verify public-web egress, rate limits and persistence on the selected host. Mount an approved persistent `/data` volume and set `EPHEMERAL_STORAGE=false` only after restart testing. A disposable disk loses SQLite data. This release does not include a Supabase/Turso connector.
6. Protected deployment refuses private uploads. Localhost upload parsing has time/size bounds but lacks an OS network sandbox on Windows; do not accept untrusted public uploads.

Hugging Face Docker Spaces can use the container on port 7860. Eligibility, privacy, uptime and persistent disk depend on the account; no free hosting promise is made. `packages.txt` documents Tesseract system packages for hosts that support that mechanism. The default synthetic image does not need OCR. If enabling OCR in a locally built image, install `tesseract-ocr tesseract-ocr-eng` as part of the reviewed image build.

## Optional SearXNG

Operate SearXNG separately. Copy `settings.example.yml` to ignored `settings.yml`, generate a strong `server.secret_key` privately, enable JSON, and choose a verified upstream image digest from the official registry. Bind local ports to loopback. Use authenticated HTTPS for remote hosting. Set `SEARCH_BACKEND=searxng` and the trusted operator endpoint. Never let users configure internal endpoints in the UI.

No compose file contains an unverified image digest. Engine blocks and JSON 403 responses are visible failures; the app never rotates proxies or silently substitutes a provider. Retain upstream AGPL notices and follow source obligations for modifications. See [official installation](https://docs.searxng.org/admin/installation-docker.html) and [API documentation](https://docs.searxng.org/dev/search_api.html).
