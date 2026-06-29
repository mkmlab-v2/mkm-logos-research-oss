#!/usr/bin/env python3
"""[HYPO] Assemble BTC policy promotion decision pack from rolling gate + holdout replays."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROLLING = ROOT / "reports/btrack_btc_rolling_promotion_gate_v1_latest.json"
DEFAULT_ADAPTIVE = ROOT / "reports/btrack_btc_adaptive_walkforward_gate_v1_latest.json"
DEFAULT_MARGIN = ROOT / "reports/btrack_btc_margin_walkforward_gate_v1_latest.json"
DEFAULT_TYPEA_HOLDOUT = ROOT / "reports/btrack_btc_typea_twofactor_holdout_replay_v1_latest.json"
DEFAULT_CAL_HOLDOUT = ROOT / "reports/btrack_btc_continuous_calibration_holdout_replay_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_btc_promotion_decision_pack_v1_latest.json"
SCHEMA = "btrack_btc_promotion_decision_pack_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rolling-json", type=Path, default=DEFAULT_ROLLING)
    ap.add_argument("--adaptive-json", type=Path, default=DEFAULT_ADAPTIVE)
    ap.add_argument("--margin-json", type=Path, default=DEFAULT_MARGIN)
    ap.add_argument("--typea-holdout-json", type=Path, default=DEFAULT_TYPEA_HOLDOUT)
    ap.add_argument("--cal-holdout-json", type=Path, default=DEFAULT_CAL_HOLDOUT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rolling = _load(args.rolling_json) or {}
    adaptive = _load(args.adaptive_json) or {}
    margin = _load(args.margin_json) or {}
    typea = _load(args.typea_holdout_json) or {}
    cal = _load(args.cal_holdout_json) or {}

    rolling_rec = rolling.get("promotion_recommendation") or "hold_research_only"
    adaptive_rec = adaptive.get("promotion_recommendation") or "hold_research_only"
    margin_rec = margin.get("promotion_recommendation") or "hold_research_only"
    best_rolling = rolling.get("best_policy") or {}
    best_adaptive = adaptive.get("best_family") or {}
    best_margin_adaptive = margin.get("best_adaptive_family") or {}
    best_margin_global = (margin.get("global_holdout") or {}).get("best") or {}

    final_action = "HOLD"
    promotion_rec = "hold_research_only"
    if any(
        r == "candidate_for_human_signoff"
        for r in (adaptive_rec, margin_rec, rolling_rec)
    ):
        promotion_rec = "candidate_for_human_signoff"
        final_action = "WATCH"

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_wall": "B-track — no Track A / live trading auto-merge",
        "final_action": final_action,
        "promotion_recommendation": promotion_rec,
        "would_change_active": False,
        "combined_all_passed": False,
        "best_policy_rolling": best_rolling,
        "best_family_adaptive": best_adaptive,
        "best_margin_adaptive": best_margin_adaptive,
        "best_margin_global_holdout": best_margin_global,
        "evidence": {
            "rolling_gate": str(args.rolling_json),
            "adaptive_walkforward_gate": str(args.adaptive_json),
            "margin_walkforward_gate": str(args.margin_json),
            "typea_holdout": str(args.typea_holdout_json),
            "cal_holdout": str(args.cal_holdout_json),
        },
        "margin_summary": {
            "promotion_recommendation": margin_rec,
            "train_objective": margin.get("train_objective"),
            "best_adaptive_family": best_margin_adaptive.get("family"),
            "mean_test_delta_oos": best_margin_adaptive.get("mean_test_delta_oos"),
            "positive_test_folds": best_margin_adaptive.get("positive_test_folds"),
            "global_test_delta_oos": best_margin_global.get("test_delta_oos"),
            "global_selected_params": best_margin_global.get("selected_params"),
        },
        "adaptive_summary": {
            "promotion_recommendation": adaptive_rec,
            "best_family": best_adaptive.get("family"),
            "mean_test_delta_oos": best_adaptive.get("mean_test_delta_oos"),
            "positive_test_folds": best_adaptive.get("positive_test_folds"),
            "total_folds": best_adaptive.get("total_folds"),
        },
        "rolling_summary": {
            "promotion_recommendation": rolling_rec,
            "best_policy_id": best_rolling.get("policy_id"),
            "mean_test_delta": best_rolling.get("mean_test_delta"),
        },
        "holdout_summaries": {
            "typea": {
                "canonical_holdout7_delta": (typea.get("summary") or {}).get("canonical_holdout7_delta"),
                "temporal_holdout_tail_delta": (typea.get("summary") or {}).get("temporal_holdout_tail_delta"),
                "in_sample_15d_delta": (typea.get("summary") or {}).get("in_sample_15d_delta"),
            },
            "continuous_calibration": {
                "summary": cal.get("summary"),
                "tail_inflated": cal.get("tail_delta_inflated_by_single_overlap"),
            },
        },
        "notes_ko": [
            "운영 btrack_prophecy_score_latest.json 자동 덮어쓰기 금지.",
            "승격 시에도 would_change_active=false 유지, 인간 sign-off 필수.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"final_action={final_action} promotion={promotion_rec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
