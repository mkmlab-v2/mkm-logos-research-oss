"""TKM encounter_sequence P31 physician_gold stub-free engine gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p31_gate_v1_latest.json"
KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
BACKFILL = ROOT / "reports/tkm_myeongni_engine_ledger_backfill_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p31_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p31 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p31_status") == "myeongni_engine_stub_free_ok"


def test_ledger_backfill_artifact() -> None:
    if not BACKFILL.is_file():
        pytest.skip("backfill artifact missing")
    doc = json.loads(BACKFILL.read_text(encoding="utf-8-sig"))
    assert doc.get("ok") is True


def test_physician_gold_stub_free_kpi() -> None:
    if not KPI.is_file():
        pytest.skip("myeongni kpi missing")
    doc = json.loads(KPI.read_text(encoding="utf-8-sig"))
    assert doc.get("physician_gold_engine_ok") is True
    gold = doc.get("physician_gold_only")
    assert isinstance(gold, dict)
    assert int(gold.get("stub_report_linked_count") or 0) == 0
    assert gold.get("engine_report_linked_rate") == 1.0


def test_weekly_l5_stub_free() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("1.8.0", "1.9.0", "2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    l5 = doc.get("l5_myeongni_kpi")
    assert isinstance(l5, dict)
    assert l5.get("l5_myeongni_headline_ok") is True
    assert int(l5.get("stub_report_linked_count") or 0) == 0
