#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minute-bar **shadow** eval smoke: synthetic UTC timeline + per-lens placeholder slots (B-track / report only).

Contract: docs/final/artifacts/LENS_MINUTE_SHADOW_EVAL_CONTRACT_V1.json
Does not call exchanges or drive orders. Logos / 성경 슬롯은 [NON_GATING] 해설용만 표기.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = (
    WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "lens_minute_shadow_eval_smoke_latest.json"
)
SCHEMA_ID = "lens_minute_shadow_eval_v1"


def _synthetic_lens_row(bar_index: int) -> Dict[str, Any]:
    # Deterministic pseudo-scores (not market truth).
    phase = (bar_index % 7) / 7.0
    return {
        "myeongni": {
            "direction_score": round(-1.0 + 2.0 * phase, 6),
            "confidence": round(0.5 + 0.49 * (bar_index % 3) / 3.0, 6),
            "note": "shadow_smoke_stub",
        },
        "sasang": {
            "intensity_0_1": round(phase, 6),
            "ledger_ref": None,
            "note": "shadow_smoke_stub",
        },
        "logos": {
            "interpretation_snippet": "[NON_GATING] shadow smoke — no gating",
            "risk_multiplier_cap_hint": None,
            "note": "shadow_smoke_stub",
        },
    }


def build_report(*, bars: int, interval_minutes: int, asset_id: str) -> Dict[str, Any]:
    if bars < 1 or bars > 10_000:
        raise ValueError("bars must be in [1, 10000]")
    if interval_minutes < 1 or interval_minutes > 1440:
        raise ValueError("interval_minutes must be in [1, 1440]")

    base = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    rows: List[Dict[str, Any]] = []
    for i in range(bars):
        ts = base + timedelta(minutes=interval_minutes * i)
        rows.append(
            {
                "bar_ts_utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "bar_index": i,
                "asset_id": asset_id,
                "lens_minute_snapshot": _synthetic_lens_row(i),
            }
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA_ID,
        "schema_version": "1.0.0",
        "generated_at_utc": now,
        "shadow_only": True,
        "no_trading_action": True,
        "bar_interval_minutes": interval_minutes,
        "dataset_note": "synthetic_timeline_for_contract_smoke — replace with OHLCV-aligned feeds when wiring adapters",
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Lens minute shadow eval smoke (synthetic).")
    ap.add_argument("--bars", type=int, default=8, help="Number of minute bars (default 8).")
    ap.add_argument(
        "--interval-minutes",
        type=int,
        default=1,
        dest="interval_minutes",
        help="Bar size in minutes (default 1).",
    )
    ap.add_argument(
        "--asset-id",
        default="BTC_SHADOW_SMOKE",
        help="Instrument label for the smoke report.",
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSON (default: {DEFAULT_OUT}).",
    )
    args = ap.parse_args()

    report = build_report(
        bars=args.bars,
        interval_minutes=args.interval_minutes,
        asset_id=args.asset_id,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
