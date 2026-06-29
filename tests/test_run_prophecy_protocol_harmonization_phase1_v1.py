"""Phase 1 protocol harmonization smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_phase1_harmonization_report() -> None:
    out = ROOT / "reports/prophecy_protocol_harmonization_phase1_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_prophecy_protocol_harmonization_phase1_v1.py")],
            cwd=str(ROOT),
            timeout=900,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_protocol_harmonization_phase1_v1"
    assert doc.get("ok") is True
    assert doc.get("protocol", {}).get("neutral_bps") == 5.0
    assert doc.get("protocol", {}).get("recent_trading_days") == 252
    rq = doc.get("rq025_reference_kospi_252d_5bps") or {}
    assert rq.get("per_date_kospi_ensemble_pooled_hr") is not None
    inst = (doc.get("recommended_chain_252d_5bps") or {}).get("instrument_combo_walkforward") or {}
    assert inst.get("mean_test_accuracy") is not None
