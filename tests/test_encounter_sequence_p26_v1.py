"""TKM encounter_sequence P26 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p26_gate_v1_latest.json"
OPS = ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json"


def test_p26_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p26 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p26_status") == "ops_closure_ok"


def test_ops_closure_items() -> None:
    if not OPS.is_file():
        pytest.skip("ops closure missing")
    doc = json.loads(OPS.read_text(encoding="utf-8-sig"))
    assert doc.get("closure_ok") is True
    items = doc.get("items")
    assert isinstance(items, dict)
    for key in ("1_daily_capture", "2_curated_learning_ack", "3_fact_lock_bundle", "6_export_ingest"):
        assert (items.get(key) or {}).get("ok") is True
