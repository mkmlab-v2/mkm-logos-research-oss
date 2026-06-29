"""v5 operational adapter promotion gates."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v5_ops_promotion_dry_run_exits_0() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_myeongri_interpret_v5_operational_adapter_promotion_v1.py"),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["ok"] is True
    assert out["applied"] is False
