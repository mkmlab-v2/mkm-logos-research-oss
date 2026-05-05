#!/usr/bin/env python3
"""Build fixed daily indicator mapping for Sasang 4-constitution regime model."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "sasang_daily_indicator_mapping_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    payload = {
        "schema": "sasang_daily_indicator_mapping_v1",
        "generated_at_utc": _now(),
        "timeframe": "1d",
        "indicator_params_fixed": {
            "adx_period": 14,
            "rsi_period": 14,
            "atr_period": 14,
            "bb_period": 20,
            "bb_stddev": 2.0,
            "obv_window": 20,
            "volume_z_window": 60,
            "wick_ratio_window": 20,
        },
        "constitution_rules": {
            "taeyang": {
                "intent": "expansion_breakout",
                "conditions_all": [
                    "adx14 >= 22",
                    "obv_z20 >= 1.0",
                    "close_above_bb_mid == true",
                ],
            },
            "soyanga": {
                "intent": "volatile_whipsaw",
                "conditions_all": [
                    "atr14_z60 >= 1.0",
                    "wick_ratio_z20 >= 0.8",
                ],
            },
            "taeeum": {
                "intent": "compression_accumulation",
                "conditions_all": [
                    "bb_width_z60 <= -0.8",
                    "volume_z60 <= -0.5",
                ],
            },
            "soeum": {
                "intent": "panic_contraction",
                "conditions_all": [
                    "rsi14 <= 30",
                    "down_volume_z60 >= 0.8",
                ],
            },
        },
        "priority_order": ["soeum", "taeyang", "soyanga", "taeeum"],
        "policy_contract": {
            "use_as": "veto_or_regime_filter_first",
            "directional_trigger_default": "disabled",
            "promotion_fasttrack": {
                "veto_only_when": {
                    "mdd_improved_ratio_gte": 0.6,
                    "cvar_improved_ratio_gte": 0.6,
                    "pvalue_lt": 0.05,
                }
            },
        },
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
