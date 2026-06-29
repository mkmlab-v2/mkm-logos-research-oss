# Purpose: permissions.json smoke contract.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_permissions_smoke_passes() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_cursor_permissions_smoke_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(
        (ROOT / "reports/cursor_permissions_smoke_latest.json").read_text(encoding="utf-8")
    )
    assert doc["ok"] is True
