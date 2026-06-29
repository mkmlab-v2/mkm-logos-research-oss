#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tier-2+ severe-stage knife breakdown for envelope equity basket [HYPO][research_only]."""
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
    aggregate_signal_metrics,
    download_yf_rows,
    eval_entry_directional_hits,
    load_features_from_rows,
    summarize_severe_knife_signals,
)
from scripts.run_envelope_ma_equity_basket_backtest_hypo_v1 import (  # noqa: E402
    ARMS,
    TIER2_BASKET,
    _eval_dates_from_score,
)

DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_EQUITY = ROOT / "reports/btrack_envelope_equity_basket_backtest_hypo_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_envelope_severe_knife_panel_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_features_by_symbol(*, download_start: str) -> tuple[dict[str, dict[str, dict[str, Any]]], list[dict[str, str]]]:
    features_by_symbol: dict[str, dict[str, dict[str, Any]]] = {}
    errors: list[dict[str, str]] = []
    for item in TIER2_BASKET:
        sym_id = item["id"]
        try:
            rows = download_yf_rows(item["symbol"], start=download_start)
            if not rows:
                errors.append({"symbol_id": sym_id, "error": "empty_download"})
                continue
            features_by_symbol[sym_id] = load_features_from_rows(rows)
        except Exception as exc:  # noqa: BLE001
            errors.append({"symbol_id": sym_id, "error": str(exc)[:200]})
    return features_by_symbol, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--equity-json", type=Path, default=DEFAULT_EQUITY)
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

    features_by_symbol, download_errors = _load_features_by_symbol(download_start=args.download_start)
    if not features_by_symbol:
        print("no symbols loaded", file=sys.stderr)
        return 1

    arms_out: dict[str, Any] = {}
    for arm_id in ARMS:
        per_symbol_rows: list[dict[str, Any]] = []
        per_symbol_full_metrics: list[dict[str, Any]] = []
        all_signals: list[dict[str, Any]] = []
        for item in TIER2_BASKET:
            sym_id = item["id"]
            features = features_by_symbol.get(sym_id)
            if not features:
                continue
            symbol_dates = [d for d in eval_dates if d in features]
            metrics = eval_entry_directional_hits(
                features,
                symbol_dates,
                arm_id=arm_id,
                neutral_bps=args.neutral_bps,
                subset_only=False,
                band_pct=args.band_pct,
                signal_sample_limit=None,
            )
            per_signal = metrics.get("per_signal_sample") or []
            all_signals.extend(per_signal)
            knife = summarize_severe_knife_signals(per_signal)
            per_symbol_rows.append(
                {
                    "symbol_id": sym_id,
                    "label_ko": item.get("label_ko"),
                    "yahoo_symbol": item.get("symbol"),
                    "full_window_metrics": {
                        "directional_hit_rate_raw": metrics.get("directional_hit_rate_raw"),
                        "n_entry_signals": metrics.get("n_entry_signals"),
                        "n_directional_next_day": metrics.get("n_directional_next_day"),
                    },
                    "severe_knife": knife,
                }
            )
            per_symbol_full_metrics.append({"symbol_id": sym_id, "metrics": metrics})

        arms_out[arm_id] = {
            "pooled_full_window": aggregate_signal_metrics(per_symbol_full_metrics),
            "pooled_severe_knife": summarize_severe_knife_signals(all_signals),
            "per_symbol": per_symbol_rows,
        }

    sdi_highlight: dict[str, Any] = {}
    for arm_id, arm in arms_out.items():
        for row in arm.get("per_symbol") or []:
            if row.get("symbol_id") != "samsung_sdi":
                continue
            sdi_highlight[arm_id] = row.get("severe_knife")

    doc = {
        "schema": "btrack_envelope_severe_knife_panel_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "combined_all_passed": False,
        "track_a_auto_promote": False,
        "eval_window": {
            "date_from": eval_dates[0],
            "date_to": eval_dates[-1],
            "n_trading_days": len(eval_dates),
        },
        "neutral_bps": args.neutral_bps,
        "band_pct": args.band_pct,
        "interpretation_ko": (
            "envelope dip 신호 중 smct_stage=severe 비율·익일 bear 비율 — "
            "trend_gate_v1이 차단하려는 칼날 구간 정량화; MKM·Track A 승격 무관"
        ),
        "download_errors": download_errors,
        "sources": {
            "equity_backtest_cross_check": str(args.equity_json.relative_to(ROOT)),
            "oper_score_read_only": str(args.score_json.relative_to(ROOT)),
        },
        "highlights": {"samsung_sdi_2nd_battery_proxy": sdi_highlight},
        "by_arm": arms_out,
        "verdict_ko": "research_only — severe 구간 bear-next-day는 narrative 리스크; oper score 미갱신.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK arms={len(arms_out)} symbols={len(features_by_symbol)} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
