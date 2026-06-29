"""TKM encounter_sequence P36 disagreement × resolver cross gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p36_gate_v1_latest.json"
CROSS = ROOT / "reports/tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p36_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p36 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p36_status") == "disagreement_resolver_cross_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_disagreement_resolver_cross_kpi() -> None:
    if not CROSS.is_file():
        pytest.skip("disagreement cross kpi missing")
    doc = json.loads(CROSS.read_text(encoding="utf-8-sig"))
    assert doc.get("kpi_ok") is True
    assert doc.get("non_gating") is True
    assert int(doc.get("disagreement_count") or 0) >= 1
    assert int(doc.get("disagreement_resolver_wired_count") or 0) >= 1
    assert int(doc.get("curated_learning_pointer_count") or 0) >= 1


def test_weekly_disagreement_cross_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    dr = doc.get("disagreement_resolver_cross_kpi")
    assert isinstance(dr, dict)
    assert dr.get("disagreement_resolver_headline_ok") is True
    assert dr.get("non_gating") is True
