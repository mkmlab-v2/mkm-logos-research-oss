# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


def test_doctor_runs_on_fixture_governance(tmp_path):
    gov = tmp_path / "gov.json"
    gov.write_text(
        '{"schema":"integrated_governance_v1","final_regime":"HOLD","final_action_allowed":false,"veto_reason_codes":["x"]}\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "athena_doctor_v1.py"), "--governance-json", str(gov), "--ecc-json", str(tmp_path / "none.json")],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "final_regime: HOLD" in proc.stdout


def test_doctor_fails_missing_governance(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "athena_doctor_v1.py"), "--governance-json", str(tmp_path / "missing.json")],
        cwd=str(_REPO),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
