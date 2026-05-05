#!/usr/bin/env python3
"""Build fixed 12-state proxy mapping for sasang pathology-pharma research."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_12state_proxy_mapping_v1_latest.json"

CONSTITUTIONS = ("taeyang", "soyanga", "taeeum", "soeum")
STAGES = ("onset", "peak", "exhaustion")
DIRECTION_BY_CONSTITUTION = {
    "taeyang": "impulse_up",
    "soyanga": "trend_up",
    "taeeum": "range_compression",
    "soeum": "risk_off_down",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stage_rules(stage: str) -> dict[str, str]:
    if stage == "onset":
        return {
            "volume_spike_z_gte": "1.2",
            "adx_cross_up_20": "true",
            "macd_signal_cross_recent_bars_lte": "3",
        }
    if stage == "peak":
        return {
            "rsi_extreme_band": "gte70_or_lte30",
            "bollinger_bandwidth_z_gte": "1.0",
            "ma_distance_z_gte": "1.2",
        }
    return {
        "momentum_divergence_present": "true",
        "atr_regime_shift": "squeeze_or_burst",
        "volume_price_confirmation_break": "true",
    }


def main() -> int:
    states: list[dict[str, object]] = []
    for constitution in CONSTITUTIONS:
        for stage in STAGES:
            state_id = f"{constitution}_{stage}"
            states.append(
                {
                    "state_id": state_id,
                    "constitution": constitution,
                    "stage": stage,
                    "direction_profile": DIRECTION_BY_CONSTITUTION[constitution],
                    "proxy_rules": _stage_rules(stage),
                    "veto_watchlist": stage == "exhaustion",
                }
            )

    payload = {
        "schema": "sasang_12state_proxy_mapping_v1",
        "generated_at_utc": _now_utc(),
        "fixed_params": {
            "adx_period": 14,
            "rsi_period": 14,
            "atr_period": 14,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "bollinger_period": 20,
            "bollinger_stddev": 2.0,
        },
        "state_count": len(states),
        "states": states,
        "validation_contract": {
            "minimum_samples_per_state": 80,
            "walkforward": {"train_years": 10, "test_years": 2, "rolling": True},
            "promotion_gate": {
                "accuracy_primary_required": False,
                "veto_only_fasttrack_when": {
                    "mdd_reduction_pct_gte": 10.0,
                    "cvar_improvement_pct_gte": 8.0,
                    "p_value_lt": 0.05,
                },
            },
        },
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
