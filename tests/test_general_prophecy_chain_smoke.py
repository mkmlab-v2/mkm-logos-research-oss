# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke subprocess for general prophecy CLI (no network).

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_generate_general_prophecy_dry_run() -> None:
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"), "--dry-run"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_eval_general_prophecy_brier_stdout_on_fixture() -> None:
    fx = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(fx),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "general_prophecy_brier_eval_v1" in r.stdout
