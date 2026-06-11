"""[HYPO] compression open-bench internal persuasion deck builder."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_persuasion_deck_hold_and_roi(tmp_path: Path) -> None:
    dual = {
        "corpora_and_skus": [
            {
                "label": "golden40_public_safe_routed",
                "present": True,
                "non_zero_saving": True,
                "sku_id": "MKM-CHAT-D1",
                "forced_shard_id": "zone_d_ssot_b2b_v1",
                "case_count": 40,
                "raw": {
                    "mean_token_saving_rate_proxy": 0.0936,
                    "saving_pct_display": 9.36,
                    "mean_jaccard_proxy": 0.897,
                },
            }
        ]
    }
    dual_path = tmp_path / "dual.json"
    dual_path.write_text(json.dumps(dual), encoding="utf-8")
    out_path = tmp_path / "deck.json"

    import scripts.build_compression_open_bench_persuasion_deck_v1 as mod

    doc = mod.build(dual_path=dual_path)
    assert doc["send_gate"] == "HOLD"
    assert doc["ready_for_external_send"] is False
    assert len(doc["illustrative_roi_scenarios_krw"]) == 3
    assert doc["illustrative_roi_scenarios_krw"][0]["illustrative_monthly_save_krw"] == 9_360_000

    rc = mod.main(["--dual-json", str(dual_path), "--output", str(out_path)])
    assert rc == 0
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["schema"] == "compression_open_bench_persuasion_deck_v1"


def test_v2_lane_freeze_from_smoke(tmp_path: Path) -> None:
    smoke = {
        "v1_aggregate": {"mean_test_accuracy": 0.535},
        "v2_aggregate": {"mean_test_accuracy": 0.528},
        "delta_mean_v2_minus_v1": -0.007,
    }
    smoke_path = tmp_path / "smoke.json"
    smoke_path.write_text(json.dumps(smoke), encoding="utf-8")

    import scripts.build_rq024_btc_lens_v2_lane_freeze_v1 as mod

    doc = mod.build(smoke_path=smoke_path)
    assert doc["status"] == "frozen_r_and_d"
    assert doc["delta_v2_minus_v1"] == -0.007
