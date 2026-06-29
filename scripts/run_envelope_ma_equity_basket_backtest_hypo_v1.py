#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tier-2 named equity basket envelope backtest [HYPO][research_only]."""
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
    DEFAULT_NEUTRAL_BPS,
    SUBSET_ENVELOPE_TREND_GATE_V1,
    SUBSET_LEGACY_LIGHT_MEDIUM,
    aggregate_signal_metrics,
    download_yf_rows,
    eval_entry_directional_hits,
    load_features_from_rows,
)

DEFAULT_OUT = ROOT / "reports/btrack_envelope_equity_basket_backtest_hypo_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
ARMS = ("arm_a_naked_60d_6", "arm_b_trend_filtered", "arm_c_120d_up_60d_pullback")

TIER2_BASKET: list[dict[str, str]] = [
    {"id": "hyundai_motor", "label_ko": "현대차", "symbol": "005380.KS"},
    {"id": "kia", "label_ko": "기아", "symbol": "000270.KS"},
    {"id": "lg_chem", "label_ko": "LG화학", "symbol": "051910.KS"},
    {"id": "samsung_heavy", "label_ko": "삼성중공업", "symbol": "010140.KS"},
    {"id": "doosan_enerbility", "label_ko": "두산에너빌리티", "symbol": "034020.KS"},
    {"id": "samsung_sdi", "label_ko": "2차전지_proxy_삼성SDI", "symbol": "006400.KS"},
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval_dates_from_score(score_path: Path) -> list[str]:
    doc = json.loads(score_path.read_text(encoding="utf-8"))
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict) and r.get("instrument") == "kospi"]
    return sorted(str(r["eval_date"])[:10] for r in rows if r.get("eval_date"))


def _run_arm_for_basket(
    *,
    arm_id: str,
    eval_dates: list[str],
    features_by_symbol: dict[str, dict[str, dict[str, Any]]],
    meta_by_symbol: dict[str, dict[str, str]],
    neutral_bps: float,
    band_pct: float,
) -> dict[str, Any]:
    per_symbol_full: list[dict[str, Any]] = []
    per_symbol_legacy: list[dict[str, Any]] = []
    per_symbol_trend: list[dict[str, Any]] = []
    symbol_rows_full: list[dict[str, Any]] = []
    symbol_rows_legacy: list[dict[str, Any]] = []
    symbol_rows_trend: list[dict[str, Any]] = []
    for sym_id, features in features_by_symbol.items():
        meta = meta_by_symbol[sym_id]
        symbol_dates = [d for d in eval_dates if d in features]
        full = eval_entry_directional_hits(
            features,
            symbol_dates,
            arm_id=arm_id,
            neutral_bps=neutral_bps,
            subset_only=False,
            band_pct=band_pct,
        )
        subset_legacy = eval_entry_directional_hits(
            features,
            symbol_dates,
            arm_id=arm_id,
            neutral_bps=neutral_bps,
            subset_mode=SUBSET_LEGACY_LIGHT_MEDIUM,
            band_pct=band_pct,
        )
        subset_trend = eval_entry_directional_hits(
            features,
            symbol_dates,
            arm_id=arm_id,
            neutral_bps=neutral_bps,
            subset_mode=SUBSET_ENVELOPE_TREND_GATE_V1,
            band_pct=band_pct,
        )
        symbol_rows_full.append(
            {
                "symbol_id": sym_id,
                "label_ko": meta.get("label_ko"),
                "yahoo_symbol": meta.get("symbol"),
                "n_eval_days_aligned": len(symbol_dates),
                "metrics": full,
                "smct_subset_legacy_metrics": subset_legacy,
                "envelope_trend_gate_v1_metrics": subset_trend,
            }
        )
        symbol_rows_legacy.append(
            {"symbol_id": sym_id, "label_ko": meta.get("label_ko"), "yahoo_symbol": meta.get("symbol"), "metrics": subset_legacy}
        )
        symbol_rows_trend.append(
            {"symbol_id": sym_id, "label_ko": meta.get("label_ko"), "yahoo_symbol": meta.get("symbol"), "metrics": subset_trend}
        )
        per_symbol_full.append({"symbol_id": sym_id, "metrics": full})
        per_symbol_legacy.append({"symbol_id": sym_id, "metrics": subset_legacy})
        per_symbol_trend.append({"symbol_id": sym_id, "metrics": subset_trend})

    return {
        "full_window": {
            "pooled": aggregate_signal_metrics(per_symbol_full),
            "per_symbol": symbol_rows_full,
        },
        "smct_subset_legacy_light_medium": {
            "pooled": aggregate_signal_metrics(per_symbol_legacy),
            "per_symbol": symbol_rows_legacy,
        },
        "envelope_trend_gate_v1": {
            "pooled": aggregate_signal_metrics(per_symbol_trend),
            "per_symbol": symbol_rows_trend,
        },
        "smct_subset": {
            "pooled": aggregate_signal_metrics(per_symbol_legacy),
            "per_symbol": symbol_rows_legacy,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--neutral-bps", type=float, default=DEFAULT_NEUTRAL_BPS)
    ap.add_argument("--band-pct", type=float, default=0.06)
    ap.add_argument("--download-start", type=str, default="2020-01-01")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.score_json.is_file():
        print(f"missing score json: {args.score_json}", file=sys.stderr)
        return 1

    eval_dates = _eval_dates_from_score(args.score_json)
    if not eval_dates:
        print("no kospi eval dates", file=sys.stderr)
        return 1

    features_by_symbol: dict[str, dict[str, dict[str, Any]]] = {}
    meta_by_symbol: dict[str, dict[str, str]] = {}
    download_errors: list[dict[str, str]] = []

    for item in TIER2_BASKET:
        sym_id = item["id"]
        symbol = item["symbol"]
        meta_by_symbol[sym_id] = item
        try:
            rows = download_yf_rows(symbol, start=args.download_start)
            if not rows:
                download_errors.append({"symbol_id": sym_id, "error": "empty_download"})
                continue
            features_by_symbol[sym_id] = load_features_from_rows(rows)
        except Exception as exc:  # noqa: BLE001 — research script; record and continue
            download_errors.append({"symbol_id": sym_id, "error": str(exc)[:200]})

    if not features_by_symbol:
        print("no symbols loaded", file=sys.stderr)
        return 1

    arms_out: dict[str, Any] = {}
    for arm in ARMS:
        arms_out[arm] = _run_arm_for_basket(
            arm_id=arm,
            eval_dates=eval_dates,
            features_by_symbol=features_by_symbol,
            meta_by_symbol=meta_by_symbol,
            neutral_bps=args.neutral_bps,
            band_pct=args.band_pct,
        )

    doc = {
        "schema": "btrack_envelope_equity_basket_backtest_hypo_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "track_a_auto_promote": False,
        "fairness": "weak",
        "fairness_note_ko": "개별주 envelope vs MKM kospi leg — MKM은 종목 신호 아님; narrative/research only",
        "eval_window": {"date_from": eval_dates[0], "date_to": eval_dates[-1], "n_trading_days": len(eval_dates)},
        "neutral_bps": args.neutral_bps,
        "band_pct": args.band_pct,
        "basket": TIER2_BASKET,
        "download_errors": download_errors,
        "n_symbols_loaded": len(features_by_symbol),
        "arms": arms_out,
        "mkm_reference_read_only": {
            "score_json": str(args.score_json.relative_to(ROOT)),
            "kospi_leg_note": "compare narrative only; not same universe",
        },
        "design_ssot": "reports/btrack_envelope_ma_vs_prophecy_benchmark_hypo_v1_latest.json tier2",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK symbols={len(features_by_symbol)} eval_days={len(eval_dates)} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
