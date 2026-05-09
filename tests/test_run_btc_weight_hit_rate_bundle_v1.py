# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test for BTC weight × hit-rate bundle script (dry-run only).
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_btc_weight_hit_rate_bundle_v1.py"


def test_bundle_script_exists() -> None:
    assert _SCRIPT.is_file()


def test_dry_run_exits_zero() -> None:
    cp = subprocess.run(
        [sys.executable, str(_SCRIPT), "--dry-run"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
