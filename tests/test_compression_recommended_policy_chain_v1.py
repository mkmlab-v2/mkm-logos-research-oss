"""Smoke: compression recommended policy — baseline or promoted min_pair."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCM_SHARD = ROOT / "codebook" / "shards" / "zone_a_scm.json"
BASELINE_SOFT = ["증상", "처방", "금칙", "단위", "안전하다"]
MIN_PAIR = ["일반화하면", "손실되면"]
PRODUCTION_MIN_PAIR = BASELINE_SOFT + MIN_PAIR
PIN_PROD = ROOT / "docs" / "final" / "artifacts" / "compression_scm_shard_pin_v1.json"
WAIVER = ROOT / "docs" / "final" / "artifacts" / "compression_cmp2_min_pair_promotion_waiver_v1.json"
SWEEP = ROOT / "docs" / "final" / "artifacts" / "compression_cmp2_local_mustkeep_sweep_20260518_v1.json"


def _promoted() -> bool:
    return WAIVER.is_file()


def test_production_shard_soft_terms_match_policy() -> None:
    doc = json.loads(SCM_SHARD.read_text(encoding="utf-8"))
    expected = PRODUCTION_MIN_PAIR if _promoted() else BASELINE_SOFT
    assert doc.get("must_keep_soft_terms") == expected


def test_pin_status_matches_promotion() -> None:
    pin = json.loads(PIN_PROD.read_text(encoding="utf-8"))
    if _promoted():
        assert pin.get("status") == "production_cmp2_min_pair"
        assert pin.get("active_kpi", {}).get("ultra_saving_policy_waived") is True
        assert pin.get("waiver_artifact")
    else:
        assert pin.get("recommendation") == "keep_baseline"
        assert pin.get("active_kpi", {}).get("ultra_saving_policy_ok") is True


def test_sweep_applied_flag_when_promoted() -> None:
    sweep = json.loads(SWEEP.read_text(encoding="utf-8"))
    rec = sweep.get("recommendation") or {}
    if _promoted():
        assert rec.get("applied_to_production") is True
        assert rec.get("production_shard") == "cmp2_min_pair"
    else:
        assert rec.get("applied_to_production") is False
