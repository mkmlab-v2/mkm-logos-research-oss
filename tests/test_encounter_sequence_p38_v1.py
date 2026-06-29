"""TKM encounter_sequence P38 export/ingest live gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p38_gate_v1_latest.json"
EXPORT_KPI = ROOT / "reports/tkm_encounter_sequence_export_ingest_kpi_v1_latest.json"
DISAGREEMENT = ROOT / "reports/tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p38_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p38 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p38_status") == "export_ingest_live_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_export_ingest_kpi() -> None:
    if not EXPORT_KPI.is_file():
        pytest.skip("export ingest kpi missing")
    doc = json.loads(EXPORT_KPI.read_text(encoding="utf-8-sig"))
    assert doc.get("kpi_ok") is True
    assert doc.get("live_ingest_ok") is True
    assert doc.get("has_l6_logos_ref") is True
    assert doc.get("has_l7_conflict_resolver_ref") is True


def test_disagreement_wired_rate() -> None:
    if not DISAGREEMENT.is_file():
        pytest.skip("disagreement cross kpi missing")
    doc = json.loads(DISAGREEMENT.read_text(encoding="utf-8-sig"))
    wired = int(doc.get("disagreement_resolver_wired_count") or 0)
    total = int(doc.get("disagreement_count") or 0)
    assert total >= 1
    assert wired / total >= 0.5


def test_weekly_export_ingest_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.4.0", "2.5.0", "2.6.0")
    ei = doc.get("export_ingest_kpi")
    assert isinstance(ei, dict)
    assert ei.get("export_ingest_headline_ok") is True
