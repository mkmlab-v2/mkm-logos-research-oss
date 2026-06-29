"""P18 general_prophecy Brier/ECE shadow eval — oracle lane."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAIN_OUT = ROOT / "reports/oracle_general_prophecy_brier_shadow_p18_chain_v1_latest.json"


@pytest.fixture(scope="module")
def p18_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_oracle_general_prophecy_brier_shadow_p18_chain_v1.py",
            "--skip-pytest",
            "--skip-harness-append",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_chain_report_pass(p18_chain: None) -> None:
    report = json.loads(CHAIN_OUT.read_text(encoding="utf-8-sig"))
    assert report["chain_pass"] is True
    assert report["metrics"]["weather_120d_sidecar"]["mean_brier_score"] < 0.05
    assert abs(report["metrics"]["weather_120d_stub"]["mean_brier_score"] - 0.25) < 1e-9


def test_production_harness_pass(p18_chain: None) -> None:
    harness = json.loads(
        (ROOT / "reports/btrack_predictability_harness_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert harness["harness_pass"] is True
    assert harness["track_wall"] == "no_track_a_auto_merge"


def test_no_logos_ssot_in_chain_note(p18_chain: None) -> None:
    report = json.loads(CHAIN_OUT.read_text(encoding="utf-8-sig"))
    assert report["track_wall"] == "no_logos_verse_ssot_mutation"
    assert report["send_gate"] == "HOLD"
