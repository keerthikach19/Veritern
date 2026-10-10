"""Group shared fee templates within one split, preserving all evidence and hashes."""

import json
from pathlib import Path

from build_fixtures import FAMILIES

root = Path(__file__).resolve().parents[1]
folder = root / "fixtures" / "synthetic"
manifest_path = folder / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
new_files = {}
for name, digest in manifest["files"].items():
    source = root / name
    data = json.loads(source.read_text(encoding="utf-8"))
    split = next(split for split, families in FAMILIES.items() if data["family"] in families)
    destination = folder / split / source.name
    assert source.resolve().is_relative_to(
        folder.resolve()
    ) and destination.resolve().is_relative_to(folder.resolve())
    if source != destination:
        if destination.exists():
            raise ValueError("Refusing to replace an existing fixture")
        source.rename(destination)
    new_files[destination.relative_to(root).as_posix()] = digest
manifest.update(version=2, families=FAMILIES, files=new_files)
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("Corpus v2: shared fee templates grouped in development; 30 cases remain in each split.")
