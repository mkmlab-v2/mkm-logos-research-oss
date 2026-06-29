# -*- coding: utf-8 -*-
"""Smoke: Logos 4D topic spike CI policy — organic gate must stay demoted."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/logos_4d_topic_spike_ci_policy_v1.json"
CHECK = ROOT / "scripts/check_logos_4d_topic_spike_ci_policy_v1.py"


def test_ci_policy_organic_gate_demoted() -> None:
    doc = json.loads(POLICY.read_text(encoding="utf-8-sig"))
    organic = (doc.get("policy") or {}).get("organic_seed_intersection_top_k") or {}
    assert organic.get("promotion_gate") is False
    assert organic.get("required_for_ci_pass") is False
    assert doc.get("research_only") is True
    assert (doc.get("track_wall") or {}).get("compression_track_a_touch") is False


def test_check_script_policy_validation_exits_zero() -> None:
    cp = subprocess.run(
        [sys.executable, str(CHECK), "--skip-pytest", "--skip-gold-check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
