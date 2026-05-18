"""Model swap harness dry-run and import smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_model_swap_harness_dry_run() -> None:
    out = ROOT / "reports" / "_tmp_model_swap_harness_dry.json"
    r = subprocess.run(
        [
            sys.executable,
            "scripts/run_btrack_model_swap_harness_v1.py",
            "--dry-run",
            "--output",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_model_swap_harness_v1"
    assert doc["dry_run"] is True
    assert doc["auto_promote"] is False
    out.unlink(missing_ok=True)


def test_frozen_baseline_constant() -> None:
    from scripts.run_btrack_model_swap_harness_v1 import FROZEN_BASELINE_HEADLINE

    assert abs(FROZEN_BASELINE_HEADLINE - 0.366667) < 1e-6
