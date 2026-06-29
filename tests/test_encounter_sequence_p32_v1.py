"""TKM encounter_sequence P32 L6 Logos cosmic anchor wire gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p32_gate_v1_latest.json"
LOGOS_KPI = ROOT / "reports/tkm_encounter_sequence_logos_kpi_v1_latest.json"
SEPARATION = ROOT / "reports/tkm_logos_sasang_lens_separation_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p32_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p32 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p32_status") == "logos_cosmic_anchor_wire_ok"


def test_logos_kpi_physician_gold() -> None:
    if not LOGOS_KPI.is_file():
        pytest.skip("logos kpi missing")
    doc = json.loads(LOGOS_KPI.read_text(encoding="utf-8-sig"))
    assert doc.get("physician_gold_logos_ok") is True
    gold = doc.get("physician_gold_only")
    assert isinstance(gold, dict)
    assert gold.get("logos_anchor_linked_rate") == 1.0


def test_logos_lens_separation() -> None:
    if not SEPARATION.is_file():
        pytest.skip("logos separation missing")
    doc = json.loads(SEPARATION.read_text(encoding="utf-8-sig"))
    assert doc.get("separation_ok") is True


def test_weekly_l6_logos_kpi() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("1.9.0", "2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    l6 = doc.get("l6_logos_kpi")
    assert isinstance(l6, dict)
    assert l6.get("l6_logos_headline_ok") is True
    assert l6.get("non_gating") is True


def test_l6_sidecar_points_to_cosmic_anchor_batch() -> None:
    import importlib.util

    path = ROOT / "scripts/tkm_encounter_sequence_logos_sidecar_v1.py"
    spec = importlib.util.spec_from_file_location("logos_sidecar", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    anchor = mod.load_anchor("seed")
    assert anchor is not None
    assert anchor.get("schema") == "logos_cosmic_anchor_formalization_v1"
    fact = anchor.get("fact_lock") or {}
    assert fact.get("non_gating") is True
