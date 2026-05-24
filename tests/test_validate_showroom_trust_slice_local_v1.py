# Keywords: validate_showroom_trust_slice_local_v1

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_validate_local_slice_script_exists() -> None:
    script = ROOT / "scripts" / "validate_showroom_trust_slice_local_v1.py"
    assert script.is_file()


def test_validate_local_fails_on_missing_slice(tmp_path: Path) -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_showroom_trust_slice_local_v1.py"),
            "--slice",
            str(tmp_path / "missing.json"),
            "--html",
            str(tmp_path / "missing.html"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
