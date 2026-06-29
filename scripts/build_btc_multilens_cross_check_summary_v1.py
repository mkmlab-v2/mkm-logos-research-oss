#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aggregate BTC multilens cross-check artifacts [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btc_multilens_cross_check_summary_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _lens3_metrics(doc: dict[str, Any]) -> dict[str, Any]:
    direct = doc.get("v2_lens3_heavy")
    if isinstance(direct, dict):
        return dict(direct.get("metrics") or {})
    for row in doc.get("variants") or []:
        if row.get("variant_id") == "v2_lens3_heavy":
            return dict(row.get("metrics") or {})
    return {}


def build_summary() -> dict[str, Any]:
    btc_full = _read_json(ROOT / "reports/btc_multilens_blend_backtest_latest.json")
    btc_140 = _read_json(ROOT / "reports/btc_multilens_blend_backtest_140d_latest.json")
    btc_wf = _read_json(ROOT / "reports/btc_multilens_walkforward_backtest_latest.json")
    kospi_140 = _read_json(ROOT / "reports/kospi_multilens_blend_backtest_latest.json")
    horizon = _read_json(ROOT / "reports/three_lens_horizon_empirical_eval_v2_latest.json")
    combo_wf = _read_json(ROOT / "docs/final/artifacts/prophecy_instrument_combo_walkforward_v1_latest.json")

    btc_csv_rows = 0
    btc_csv_path = ROOT / "research/market_data/btc_daily_external_yf.csv"
    if btc_csv_path.is_file():
        btc_csv_rows = max(0, sum(1 for _ in btc_csv_path.open(encoding="utf-8-sig")) - 1)

    l3_full = _lens3_metrics(btc_full)
    l3_140 = _lens3_metrics(btc_140)
    k3_140 = _lens3_metrics(kospi_140)

    wf_sum = btc_wf.get("summary") if isinstance(btc_wf.get("summary"), dict) else {}
    top2 = wf_sum.get("recommended_prefilter_variants_top2") or []
    lens3_top2 = any(str(v).startswith("v2_lens3_heavy") for v in top2)
    if "v2_lens3_heavy_in_top2" not in wf_sum:
        wf_sum = {**wf_sum, "v2_lens3_heavy_in_top2": lens3_top2}
    else:
        wf_sum = {**wf_sum, "v2_lens3_heavy_in_top2": bool(wf_sum.get("v2_lens3_heavy_in_top2")) or lens3_top2}
    hz_btc = (horizon.get("legs") or {}).get("btc") if isinstance(horizon.get("legs"), dict) else {}
    combo_inputs = combo_wf.get("inputs") if isinstance(combo_wf.get("inputs"), dict) else {}
    combo_agg = combo_wf.get("aggregate") if isinstance(combo_wf.get("aggregate"), dict) else {}
    combo_folds = combo_wf.get("folds") if isinstance(combo_wf.get("folds"), list) else []

    return {
        "schema": "btc_multilens_cross_check_summary_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "btc_csv": {"path": str(btc_csv_path), "rows": btc_csv_rows},
        "v2_lens3_heavy": {
            "btc_full_window": {
                "window": btc_full.get("window"),
                "metrics": l3_full,
            },
            "btc_140d_window": {
                "window": btc_140.get("window"),
                "metrics": l3_140,
            },
            "kospi_140d_reference": {
                "window": kospi_140.get("window"),
                "metrics": k3_140,
            },
            "delta_btc_minus_kospi_soft_140d": (
                round(float(l3_140.get("soft_hit_rate")) - float(k3_140.get("soft_hit_rate")), 4)
                if l3_140.get("soft_hit_rate") is not None and k3_140.get("soft_hit_rate") is not None
                else None
            ),
        },
        "btc_walkforward": {
            "n_folds": wf_sum.get("n_folds"),
            "selection_top1_hit_rate": wf_sum.get("selection_top1_hit_rate"),
            "top2": wf_sum.get("recommended_prefilter_variants_top2"),
            "v2_lens3_heavy_in_top2": wf_sum.get("v2_lens3_heavy_in_top2"),
            "v2_lens3_heavy_mean_test_soft": wf_sum.get("v2_lens3_heavy_mean_test_soft"),
        },
        "horizon_v2_btc_leg": {
            "n_eval_dates": (hz_btc.get("v1_direction_eval") or {}).get("n_eval_dates"),
            "summary": horizon.get("summary", {}).get("btc") if isinstance(horizon.get("summary"), dict) else None,
        },
        "instrument_combo_walkforward": {
            "schema": combo_wf.get("schema"),
            "n_folds": combo_inputs.get("n_walkforward_folds") or len(combo_folds) or None,
            "dual_leg_eval_dates": combo_inputs.get("n_distinct_eval_dates"),
            "mean_test_accuracy": combo_agg.get("mean_test_accuracy"),
            "beats_always_bull_frac": combo_agg.get("beats_always_bull_frac_test"),
        },
        "verdict_ko": _verdict_ko(l3_full, l3_140, k3_140, wf_sum),
    }


def _verdict_ko(
    l3_full: dict[str, Any],
    l3_140: dict[str, Any],
    k3_140: dict[str, Any],
    wf_sum: dict[str, Any],
) -> str:
    parts: list[str] = []
    soft_full = l3_full.get("soft_hit_rate")
    if soft_full is not None:
        parts.append(f"BTC 전구간 lens3 soft={soft_full}")
    if l3_140.get("soft_hit_rate") is not None and k3_140.get("soft_hit_rate") is not None:
        parts.append(
            f"140일창 BTC={l3_140.get('soft_hit_rate')} vs KOSPI={k3_140.get('soft_hit_rate')}"
        )
    top2 = wf_sum.get("recommended_prefilter_variants_top2") or []
    if any(str(v).startswith("v2_lens3_heavy") for v in top2):
        parts.append("WF top2 포함(lens3 family)")
    else:
        parts.append("WF top2 미포함")
    parts.append("June apply·Track A 자동 합선 없음 [HYPO]")
    return " · ".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    doc = build_summary()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} verdict={doc.get('verdict_ko')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
