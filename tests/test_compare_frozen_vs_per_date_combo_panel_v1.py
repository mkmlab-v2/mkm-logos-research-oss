"""Smoke tests for frozen vs per-date panel compare."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_metrics_on_stub_rows() -> None:
    path = ROOT / "scripts/compare_frozen_vs_per_date_combo_panel_v1.py"
    spec = importlib.util.spec_from_file_location("compare_frozen_vs_per_date_combo_panel_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)

    rows = [
        {"instrument": "btc", "eval_date": "2026-04-02", "predicted_direction": "bear", "actual_direction": "bear"},
        {"instrument": "btc", "eval_date": "2026-04-03", "predicted_direction": "bear", "actual_direction": "bull"},
    ]
    m = mod._frozen_metrics(rows)
    assert m["price_hits"] == 1
    assert m["n_evaluated"] == 2
    assert m["frozen_direction"] == "bear"


def test_latest_compare_artifact_schema() -> None:
    p = ROOT / "reports/frozen_vs_per_date_panel_compare_v1_latest.json"
    if not p.is_file():
        return
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc.get("schema") == "frozen_vs_per_date_panel_compare_v1"
    assert doc.get("track_a_mutated") is False
    comp = doc.get("comparison") or {}
    assert "frozen_single_direction_batch" in comp
    assert comp["frozen_single_direction_batch"]["price_directional_hit_rate"] == 0.433333
    lines = doc.get("alert_lines") or []
    assert any("[MKM-DUAL-KPI]" in str(x) for x in lines)
