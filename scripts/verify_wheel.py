"""Check installed-layout imports and bundled evaluation data using current dependencies."""

import subprocess
import sys
import zipfile
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
archive = root / "dist" / "veritern-0.1.0-py3-none-any.whl"
destination = root / "dist" / ("wheel-check-" + uuid4().hex[:8])
destination.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as wheel:
    for name in wheel.namelist():
        if not (destination / name).resolve().is_relative_to(destination.resolve()):
            raise ValueError("Unsafe archive path")
    wheel.extractall(destination)
code = "import sys; sys.path.insert(0, sys.argv[1]); import veritern; from veritern.cli import evaluate; print('Wheel package:', veritern.__file__); assert evaluate('heldout')"
subprocess.run([sys.executable, "-I", "-c", code, str(destination)], check=True, cwd=root / "dist")
