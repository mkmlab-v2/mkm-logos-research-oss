"""TKM encounter_sequence P35 3-lens conflict resolver gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p35_gate_v1_latest.json"
RESOLVER = ROOT / "reports/tkm_encounter_sequence_conflict_resolver_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p35_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p35 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p35_status") == "conflict_resolver_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_conflict_resolver_kpi() -> None:
    if not RESOLVER.is_file():
        pytest.skip("conflict resolver kpi missing")
    doc = json.loads(RESOLVER.read_text(encoding="utf-8-sig"))
    assert doc.get("kpi_ok") is True
    assert doc.get("non_gating") is True
    assert int(doc.get("conflict_resolver_wired_count") or 0) >= 1
    assert doc.get("physician_gold_conflict_resolver_ok") is True
    assert int(doc.get("separation_violation_count") or 0) == 0


def test_weekly_conflict_resolver_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.1.0", "2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    cr = doc.get("conflict_resolver_kpi")
    assert isinstance(cr, dict)
    assert cr.get("conflict_resolver_headline_ok") is True
    assert cr.get("non_gating") is True
