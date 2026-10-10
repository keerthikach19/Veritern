"""Record installed metadata and preserve available bundled license notices."""

import importlib.metadata as metadata
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "docs" / "licenses"
folder.mkdir(parents=True, exist_ok=True)
report = []
for distribution in sorted(
    metadata.distributions(), key=lambda d: d.metadata.get("Name", "").lower()
):
    name = distribution.metadata.get("Name", "unknown")
    if name.lower() == "veritern":
        continue
    license_name = distribution.metadata.get("License-Expression")
    if not license_name:
        license_name = "; ".join(
            c.rsplit(" :: ", 1)[-1]
            for c in distribution.metadata.get_all("Classifier", [])
            if c.startswith("License ::")
        ) or distribution.metadata.get("License", "UNKNOWN")
    notices = []
    for file in distribution.files or []:
        if not re.search(r"(?:license|licence|notice|copying)", file.name, re.I):
            continue
        source = Path(distribution.locate_file(file))
        if (
            not source.is_file()
            or source.stat().st_size > 500000
            or source.suffix in (".py", ".pyc", ".pyd", ".dll")
        ):
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        target = folder / re.sub(r"[^a-zA-Z0-9_.-]", "_", name + "__" + str(file))
        target.write_text(text, encoding="utf-8")
        notices.append(target.relative_to(root).as_posix())
    report.append(
        {
            "name": name,
            "version": distribution.version,
            "license_metadata": license_name,
            "home_page": distribution.metadata.get("Home-page"),
            "bundled_notices": notices,
        }
    )
(root / "dependency-licenses.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)
apache = next(
    (
        file
        for file in folder.glob("groq__*")
        if "Apache License" in file.read_text(encoding="utf-8")
    ),
    None,
)
if apache:
    (root / "LICENSE").write_text(apache.read_text(encoding="utf-8"), encoding="utf-8")
print(
    f"Recorded {len(report)} installed distributions and {sum(len(row['bundled_notices']) for row in report)} notices."
)
