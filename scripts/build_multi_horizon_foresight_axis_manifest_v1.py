#!/usr/bin/env python3
"""Build 4-axis manifest for Multi-Horizon Foresight Verification [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/multi_horizon_foresight_axis_manifest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
        return o if isinstance(o, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    axes = [
        {
            "axis_id": "field_regime",
            "label_ko": "Field(레짐/환경)",
            "role": "1차 실물 regime_map 주; 최종 액션 지휘",
            "ssot": ["data/regime_map.json", "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"],
            "verification": "regime pointer + ops gates",
            "track": "ops_primary",
        },
        {
            "axis_id": "price_short",
            "label_ko": "가격(단기) — 사상 B-track",
            "role": "OHLCV hit rate / walk-forward; not alpha claim",
            "ssot": [
                "scripts/eval_prophecy_hit_rate_v1.py",
                "scripts/run_prophecy_per_date_combo_walkforward_v1.py",
            ],
            "evidence_pointer": "reports/baseline_lens_wf_ablation_v1_latest.json",
            "track": "b_track_hypo",
        },
        {
            "axis_id": "general_prophecy",
            "label_ko": "일반예언(비가격)",
            "role": "Brier/ECE/domain tags; no price merge",
            "ssot": [
                "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json",
                "scripts/eval_general_prophecy_brier_score.py",
            ],
            "track": "b_track_hypo",
        },
        {
            "axis_id": "myeongni_mid",
            "label_ko": "명리(중기)",
            "role": "개인 프로필 결정론; 시장 일진 자동 치환 금지",
            "ssot": [
                "scripts/run_myeongni_lens_chain_from_bot_v1.py",
                "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §3.3",
            ],
            "track": "deterministic_profile",
        },
        {
            "axis_id": "logos_macro",
            "label_ko": "성경(Logos) 거시",
            "role": "레짐·시나리오; [NON_GATING] — 실전 트리거 금지",
            "ssot": [
                "scripts/run_logos_4d_state_chain_v1.py",
                "scripts/build_logos_regime_resonance_shadow_signal_v1.py",
            ],
            "track": "non_gating_advisory",
        },
    ]

    doc = {
        "schema": "multi_horizon_foresight_axis_manifest_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "coordinator_mode": "Absolute Balance (state, not 5th AI)",
        "output_format": "Field → Lens(사상/명리/성경) → Conflict → Final Action (HOLD/WATCH/REDUCE)",
        "axes": axes,
        "forbidden_merges": [
            "myeongni_birth_profile_into_market_daily_pillar",
            "logos_into_live_order_trigger",
            "kospi_in_sample_into_btc_lens_promotion",
            "combined_pass_into_track_a_auto_merge",
        ],
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
