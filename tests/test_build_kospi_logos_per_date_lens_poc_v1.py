"""Smoke tests for KOSPI Logos per-date lens PoC [HYPO]."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_kospi_logos_per_date_lens_poc_v1 as builder
import scripts.kospi_logos_per_date_lens_poc_v1 as poc


def test_logos_lens_for_eval_date_uses_macro_gate(tmp_path: Path) -> None:
    gate_by_day = {
        "2026-06-04": {
            "session_date": "2026-06-04",
            "decision_state": "ELEVATED",
            "risk_warning_level": "watch",
            "schema": "test_gate",
        }
    }
    out = poc.logos_lens_for_eval_date("2026-06-04", macro_gate_by_day=gate_by_day)
    logos = out.get("logos") or {}
    assert logos.get("per_date") is True
    assert logos.get("non_gating") is True
    assert logos.get("derivation") == "macro_gate_causal_asof_v1"
    assert logos.get("direction") in ("bull", "bear", "neutral")


def test_build_kospi_logos_per_date_lens_poc_writes_schema(tmp_path: Path, monkeypatch) -> None:
    cal = {
        "rows": [
            {
                "session_date": "2026-06-01",
                "session_mapping_target": "bull",
                "session_direction_score": 0.2,
                "blend": {"weights": {}},
            }
        ]
    }
    eval_doc = {
        "rows": [
            {
                "session_date": "2026-06-01",
                "actual_direction": "bull",
            }
        ]
    }
    rules = {"neutral_band": 0.15, "blend_policy": {}}
    cal_p = tmp_path / "cal.json"
    eval_p = tmp_path / "eval.json"
    rules_p = tmp_path / "rules.json"
    cal_p.write_text(json.dumps(cal), encoding="utf-8")
    eval_p.write_text(json.dumps(eval_doc), encoding="utf-8")
    rules_p.write_text(json.dumps(rules), encoding="utf-8")

    doc = builder.build_poc(
        calendar_path=cal_p,
        eval_path=eval_p,
        rules_path=rules_p,
        myeongni_jsonl=Path("data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"),
        sasang_jsonl=Path("data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"),
        macro_jsonl=Path("reports/macro_risk/forward/macro_risk_forward_log_research_backfill_v1.jsonl"),
    )
    assert doc["schema"] == "kospi_logos_per_date_lens_poc_v1"
    assert doc["research_only"] is True
    assert doc["track_wall"]["equal_weight_logos_blend"] is False
