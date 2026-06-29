#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tier-1 KOSPI envelope arms backtest vs frozen eval window [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_envelope_smct_hypo_lib_v1 import (  # noqa: E402
    DEFAULT_KOSPI_CSV,
    DEFAULT_NEUTRAL_BPS,
    SUBSET_ENVELOPE_TREND_GATE_V1,
    SUBSET_LEGACY_LIGHT_MEDIUM,
    eval_entry_directional_hits,
    load_kospi_features,
)

DEFAULT_OUT = ROOT / "reports/btrack_envelope_ma60_6_kospi_backtest_hypo_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
ARMS = ("arm_a_naked_60d_6", "arm_b_trend_filtered", "arm_c_120d_up_60d_pullback")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval_dates_from_score(score_path: Path) -> list[str]:
    doc = json.loads(score_path.read_text(encoding="utf-8"))
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict) and r.get("instrument") == "kospi"]
    return sorted(str(r["eval_date"])[:10] for r in rows if r.get("eval_date"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=ROOT / DEFAULT_KOSPI_CSV)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--neutral-bps", type=float, default=DEFAULT_NEUTRAL_BPS)
    ap.add_argument("--band-pct", type=float, default=0.06)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.kospi_csv.is_file():
        print(f"missing kospi csv: {args.kospi_csv}", file=sys.stderr)
        return 1
    if not args.score_json.is_file():
        print(f"missing score json: {args.score_json}", file=sys.stderr)
        return 1

    eval_dates = _eval_dates_from_score(args.score_json)
    if not eval_dates:
        print("no kospi eval dates in score json", file=sys.stderr)
        return 1

    features = load_kospi_features(args.kospi_csv)
    arms_out: dict[str, Any] = {}
    for arm in ARMS:
        full = eval_entry_directional_hits(
            features,
            eval_dates,
            arm_id=arm,
            neutral_bps=args.neutral_bps,
            subset_only=False,
            band_pct=args.band_pct,
        )
        subset_legacy = eval_entry_directional_hits(
            features,
            eval_dates,
            arm_id=arm,
            neutral_bps=args.neutral_bps,
            subset_mode=SUBSET_LEGACY_LIGHT_MEDIUM,
            band_pct=args.band_pct,
        )
        subset_trend = eval_entry_directional_hits(
            features,
            eval_dates,
            arm_id=arm,
            neutral_bps=args.neutral_bps,
            subset_mode=SUBSET_ENVELOPE_TREND_GATE_V1,
            band_pct=args.band_pct,
        )
        arms_out[arm] = {
            "full_window": full,
            "smct_subset_legacy_light_medium": subset_legacy,
            "envelope_trend_gate_v1": subset_trend,
            "smct_subset": subset_legacy,
        }

    doc = {
        "schema": "btrack_envelope_ma60_6_kospi_backtest_hypo_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "track_a_auto_promote": False,
        "kospi_csv": str(args.kospi_csv.relative_to(ROOT)) if args.kospi_csv.is_relative_to(ROOT) else str(args.kospi_csv),
        "score_json_read_only": str(args.score_json.relative_to(ROOT)) if args.score_json.is_relative_to(ROOT) else str(args.score_json),
        "eval_window": {"date_from": eval_dates[0], "date_to": eval_dates[-1], "n_trading_days": len(eval_dates)},
        "neutral_bps": args.neutral_bps,
        "band_pct": args.band_pct,
        "kpi_note": "entry_signal -> next-day bull hit rate (not identical to MKM per-date direction eval)",
        "arms": arms_out,
        "design_ssot": [
            "reports/btrack_envelope_ma_vs_prophecy_benchmark_hypo_v1_latest.json",
            "reports/smct_market_constitution_hypo_v1_latest.json",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK eval_days={len(eval_dates)} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
