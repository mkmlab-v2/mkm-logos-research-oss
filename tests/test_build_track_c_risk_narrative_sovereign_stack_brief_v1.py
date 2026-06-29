# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke build_track_c_risk_narrative_sovereign_stack_brief_v1.py
# Keywords: track_c, sovereign_stack, general_prophecy

"""Smoke: sovereign-stack §3.2 brief pack builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_track_c_risk_narrative_sovereign_stack_brief_v1.py"
OUT = ROOT / "reports" / "track_c_risk_narrative_sovereign_stack_brief_v1.json"


def test_build_track_c_risk_narrative_sovereign_stack_brief_dry_run() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(proc.stdout)
    assert "artifact_evidence_status" in payload


def test_build_track_c_risk_narrative_sovereign_stack_brief_writes_schema() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "track_c_risk_narrative_sovereign_stack_brief_v1"
    assert doc.get("final_action") == "WATCH_SOVEREIGN_STACK"
    assert len(doc.get("measurable_backbone_question_ids") or []) == 3
