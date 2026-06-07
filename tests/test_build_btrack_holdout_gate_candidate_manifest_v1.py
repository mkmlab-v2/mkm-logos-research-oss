"""Holdout gate candidate manifest + frozen30d sweep wiring."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_holdout30d_sweep_summary_smoke() -> None:
    from scripts.build_btrack_holdout_gate_candidate_manifest_v1 import _holdout30d_sweep_summary

    sweep_path = ROOT / "reports/btrack_holdout30d_headline_sweep_v1_latest.json"
    if not sweep_path.is_file():
        return
    doc = json.loads(sweep_path.read_text(encoding="utf-8"))
    summary = _holdout30d_sweep_summary(doc)
    assert summary["pointer"].endswith("btrack_holdout30d_headline_sweep_v1_latest.json")
    assert summary["anchor_n_dates"] >= 7
    assert summary["stack_headline_delta"] == 0.0
    assert summary["hybrid_bbs_ms_frozen30d"] == 0.6


def test_gate_candidate_latest_if_present() -> None:
    p = ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json"
    if not p.is_file():
        return
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_holdout_gate_candidate_v1"
    assert doc["deployment"]["auto_promote"] is False
    h30 = doc.get("holdout30d_anchor_sweep")
    if h30:
        assert h30["stack_headline_delta"] == 0.0
        assert any("frozen30d" in line for line in doc.get("operator_lines") or [])
    hybrid = doc.get("hybrid_shadow_lane")
    if hybrid:
        assert hybrid.get("rule_slug") == "bbs_ms_agree_or_ms_else"
        assert hybrid.get("alert_1_pass_frozen30d") is True
        assert any("hybrid bbs_ms" in line for line in doc.get("operator_lines") or [])
