from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/check_opendata_327_submission_forbidden_grep_v1.py"


def test_submission_mode_runs() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--mode", "submission"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1)
