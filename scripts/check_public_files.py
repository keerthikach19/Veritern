"""Conservative pre-push check of versioned paths and obvious secret tokens."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
result = subprocess.run(
    ["git", "-c", f"safe.directory={root.as_posix()}", "ls-files", "-z"],
    cwd=root,
    capture_output=True,
    check=True,
)
paths = result.stdout.decode().split("\0")
errors = []
for name in filter(None, paths):
    path = Path(name)
    if (
        path.name == ".env"
        or name.startswith(("private_data/", ".venv/", ".venv-local/"))
        or path.suffix in (".sqlite", ".db")
        or name == ".streamlit/secrets.toml"
    ):
        errors.append(name + ": private path tracked")
    try:
        text = (root / path).read_text(encoding="utf-8")
    except (UnicodeError, OSError):
        continue
    if re.search(r"\b(?:gsk_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,}|ghp_[A-Za-z0-9]{30,})\b", text):
        errors.append(name + ": possible credential (value omitted)")
if errors:
    print("\n".join(errors))
    raise SystemExit(1)
print(
    f"Checked {len(list(filter(None, paths)))} tracked paths: no private paths or obvious API tokens."
)
