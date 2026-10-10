import hashlib
import json
from pathlib import Path

import pytest

from veritern.rules import assess
from veritern.schemas import Case

ROOT = Path(__file__).resolve().parents[2]
FILES = sorted((ROOT / "fixtures" / "synthetic").glob("*/*.json"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_frozen_case(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    case = Case.model_validate(data["case"])
    assert sorted({f.rule_id for f in assess(case)}) == sorted(data["expected_rules"])


def test_frozen_manifest_and_family_separation():
    manifest = json.loads((ROOT / "fixtures" / "synthetic" / "manifest.json").read_text())
    assert len(manifest["files"]) == 60
    assert {"free_then_fee", "batch_mismatch", "benefit_mismatch", "ocr_unreviewed"} <= set(
        manifest["families"]["development"]
    )
    assert not set(manifest["families"]["development"]) & set(manifest["families"]["heldout"])
    for name, digest in manifest["files"].items():
        assert (
            hashlib.sha256((ROOT / name).read_text(encoding="utf-8").encode()).hexdigest() == digest
        )
