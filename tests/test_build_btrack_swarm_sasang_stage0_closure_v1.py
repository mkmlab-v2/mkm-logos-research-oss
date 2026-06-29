# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_stage0_closure_builds() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/build_btrack_swarm_sasang_stage0_closure_v1.py"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    out = _ROOT / "reports/btrack_swarm_sasang_stage0_closure_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_swarm_sasang_stage0_closure_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["track_wall"]["track_a_promotion"] is False
    assert doc["stage0_complete"] is True
    assert doc["active_stage"] == 0


def test_tier_a_prereqs_exit0() -> None:
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/check_btrack_swarm_tier_a_prereqs_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert "tier_a_ready=" in r.stdout
