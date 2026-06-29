from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.build_warmth_trigger_delta_floor_v1 import build_delta_floor_report

ROOT = Path(__file__).resolve().parents[1]


def test_delta_floor_computes_and_breach_flag():
    base = {
        "rates": {"hit_rate": 0.5, "over_rate": 0.1, "hysteresis_cooldown_rate": 0.05},
        "profile_version": "base",
        "item_count": 15,
    }
    custom = {
        "rates": {"hit_rate": 0.3, "over_rate": 0.25, "hysteresis_cooldown_rate": 0.1},
        "profile_version": "custom",
        "item_count": 15,
    }
    report = build_delta_floor_report(base_batch=base, custom_batch=custom, control_limit=0.12)
    assert "delta_floor" in report
    assert report["safety_base"] > report["safety_persona_custom"]
    assert report["floor_breach"] is True


def test_cli_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_warmth_trigger_delta_floor_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
