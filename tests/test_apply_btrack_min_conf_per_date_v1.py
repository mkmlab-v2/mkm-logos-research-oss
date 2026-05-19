"""min_conf gate on per-date direction rows."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_gate_flips_low_confidence_to_neutral() -> None:
    from scripts.apply_btrack_min_conf_to_per_date_directions_v1 import apply_gate_to_document

    doc = {
        "rows": [
            {"eval_date": "2026-01-01", "predicted_direction": "bull", "confidence": 0.1},
            {"eval_date": "2026-01-02", "predicted_direction": "bear", "confidence": 0.5},
        ]
    }
    rules = {"min_direction_confidence": 0.18}
    out = apply_gate_to_document(doc, rules=rules)
    rows = out["rows"]
    assert rows[0]["predicted_direction"] == "neutral"
    assert rows[0]["low_confidence_direction_gate"]["applied"] is True
    assert rows[1]["predicted_direction"] == "bear"


def test_fair_compare_report_exists_after_chain() -> None:
    p = ROOT / "reports" / "btrack_gemini_fair_compare_v1_latest.json"
    if not p.is_file():
        return
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_gemini_fair_compare_v1"
    assert "prod_baseline_ensemble" in doc["variants"]
