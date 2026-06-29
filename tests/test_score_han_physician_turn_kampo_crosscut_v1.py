"""KampoBench cross-cut scorer — han physician turn smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.score_han_physician_turn_kampo_crosscut_v1 import score_turn_kampo_crosscut

ROOT = Path(__file__).resolve().parents[1]
LEE_TURN = ROOT / "reports" / "lee_bomi_han_physician_assist_turn_v1.json"
LEE_BUNDLE = ROOT / "reports" / "lee_bomi_patient_care_bundle_latest.json"
LEE_INTAKE = ROOT / "reports" / "lee_bomi_intake_fusion_v1.json"
LEE_LIFESTYLE = ROOT / "reports" / "lee_bomi_lifestyle_management_v2.json"


@pytest.mark.skipif(not LEE_TURN.is_file(), reason="lee_bomi turn missing")
def test_score_lee_bomi_kampo_crosscut_inprocess() -> None:
    turn = json.loads(LEE_TURN.read_text(encoding="utf-8"))
    bundle = json.loads(LEE_BUNDLE.read_text(encoding="utf-8")) if LEE_BUNDLE.is_file() else None
    intake = json.loads(LEE_INTAKE.read_text(encoding="utf-8")) if LEE_INTAKE.is_file() else None
    lifestyle = json.loads(LEE_LIFESTYLE.read_text(encoding="utf-8")) if LEE_LIFESTYLE.is_file() else None
    report = score_turn_kampo_crosscut(turn, bundle=bundle, intake=intake, lifestyle=lifestyle)
    assert report["schema"] == "kampo_bench_eval_report_v1"
    assert report.get("send_gate") == "HOLD"
    assert report.get("ref_token") == "LEE-BOMI-2026-001"
    by_id = {d["id"]: d for d in report.get("dimensions") or []}
    assert by_id["red_flag_awareness"]["status"] == "pass"
    assert by_id["syndrome_logic"]["status"] == "pass"
    assert by_id["syndrome_intake_timeseries"]["status"] == "pass"
    assert by_id["prescription_candidates"]["status"] == "pass"
    assert by_id["pro_timeseries"]["status"] == "pass"


@pytest.mark.skipif(not LEE_TURN.is_file(), reason="lee_bomi turn missing")
def test_score_cli_writes_report() -> None:
    out = ROOT / "reports" / "_pytest_lee_bomi_kampo_eval_v1.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/score_han_physician_turn_kampo_crosscut_v1.py"),
            "--han-turn-json",
            str(LEE_TURN),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert out.is_file()
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["summary"]["pass"] >= 3
    assert report["send_gate"] == "HOLD"
