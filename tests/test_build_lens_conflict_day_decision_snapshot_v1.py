"""Conflict-day decision snapshot smoke."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_lens_conflict_day_decision_snapshot_v1 import build_conflict_day_snapshot


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_shock_price_bear_yields_reduce(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    _write(
        art / "independent_lens_fusion_stub_latest.json",
        {
            "schema": "independent_lens_fusion_stub_v0",
            "ts_utc": "2026-06-08T00:15:21Z",
            "consensus": {
                "consensus_sign": "bull",
                "agreement_rate": 0.6,
                "conflict_count": 2,
            },
            "conflict_summary": {"minority_lens_ids": ["logos"]},
            "inputs": [
                {
                    "lens_id": "market_sasang",
                    "market_sasang_lens_v1": {
                        "veto_force_hold": True,
                        "veto_reason_codes": ["HIGH_ENTROPY_SOFTMAX"],
                    },
                }
            ],
        },
    )
    _write(
        art / "btrack_hypothesis_prophecy_latest.json",
        {
            "ts_utc": "2026-06-07T23:25:12Z",
            "prediction": {"instrument": "kospi", "direction": "bear", "confidence": 0.41},
            "runtime_meta": {
                "price_instrument": "kospi",
                "lens_values": {"price": {"score": -0.59, "confidence": 0.55}},
                "price_meta": {"recent_abs_return_mean": 0.03, "instrument": "kospi"},
            },
        },
    )
    _write(
        art / "global_market_overnight_signals_v1_latest.json",
        {
            "composite_tilt": "risk_off_overnight",
            "indices": [{"change_pct": -4.18}],
        },
    )
    _write(art / "macro_independent_lens_latest.json", {"scores": {"direction_score": -0.04}})
    _write(art / "news_independent_lens_latest.json", {"scores": {"direction_score": -0.07}})
    _write(art / "logos_independent_lens_latest.json", {"scores": {"direction_score": -0.32}})

    doc = build_conflict_day_snapshot(tmp_path)
    assert doc["schema"] == "lens_conflict_day_decision_snapshot_v1"
    assert doc["regime"] == "shock"
    assert doc["final_action"] == "REDUCE"
    assert doc["inputs_snapshot"]["fusion_demoted"] is True
    assert "30~40%" in doc["semi_holdings_proxy_policy_ko"]
    split = doc.get("regime_mkm_split_v1_posture") or {}
    assert split.get("schema") == "regime_mkm_split_v1_posture"
    persona = doc.get("persona_diary_myeongni_sasang_lane") or {}
    assert persona.get("schema") == "persona_diary_myeongni_sasang_lane_v1"
    fabba = doc.get("fabba_sidecar_ngram_lut") or {}
    assert fabba.get("schema") == "fabba_sidecar_ngram_lut_v1"


def test_veto_only_includes_regime_split_posture(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    reports = tmp_path / "reports"
    _write(
        art / "independent_lens_fusion_stub_latest.json",
        {
            "ts_utc": "2026-06-18T00:00:00Z",
            "consensus": {"consensus_sign": "bull", "agreement_rate": 0.8, "conflict_count": 0},
            "inputs": [
                {
                    "lens_id": "market_sasang",
                    "market_sasang_lens_v1": {
                        "veto_force_hold": True,
                        "veto_reason_codes": ["HIGH_ENTROPY_SOFTMAX"],
                    },
                }
            ],
        },
    )
    _write(
        art / "btrack_hypothesis_prophecy_latest.json",
        {
            "prediction": {"instrument": "btc", "direction": "flat", "confidence": 0.2},
            "runtime_meta": {
                "price_instrument": "btc",
                "lens_values": {"price": {"score": 0.02, "confidence": 0.4}},
                "price_meta": {"recent_abs_return_mean": 0.01},
            },
        },
    )
    _write(art / "global_market_overnight_signals_v1_latest.json", {"composite_tilt": "neutral"})
    _write(art / "macro_independent_lens_latest.json", {"scores": {"direction_score": 0.1}})
    _write(art / "news_independent_lens_latest.json", {"scores": {"direction_score": 0.05}})
    _write(art / "logos_independent_lens_latest.json", {"scores": {"direction_score": 0.0}})

    _write(
        reports / "sasang_regime_conditional_fusion_ablation_v1_latest.json",
        {
            "instruments": {
                "samsung": {
                    "policy_paths": {
                        "regime_mkm_split_tactical": {
                            "daily": [
                                {
                                    "eval_date": "2026-06-18",
                                    "force_hold": True,
                                    "supplier_tight": True,
                                    "posture": "HOLD_THROUGH_VETO",
                                    "in_market_after": True,
                                }
                            ]
                        },
                        "literal_veto_hold": {
                            "daily": [
                                {
                                    "eval_date": "2026-06-18",
                                    "force_hold": True,
                                    "supplier_tight": True,
                                    "posture": "HOLD_CASH_OR_EXIT",
                                    "in_market_after": False,
                                }
                            ]
                        },
                    }
                }
            }
        },
    )

    doc = build_conflict_day_snapshot(tmp_path)
    assert doc["final_action"] == "HOLD"
    assert doc["operator_posture"] == "human_gate_hold"
    split = doc["regime_mkm_split_v1_posture"]
    assert split["posture"] == "HOLD_THROUGH_VETO"
    assert split["diverges_from_literal_r5"] is True
    assert split["operator_posture"] == "structural_hold_block_chase_only"
    assert any("R5b_regime_mkm_split" in x for x in doc["rule_trace"])
