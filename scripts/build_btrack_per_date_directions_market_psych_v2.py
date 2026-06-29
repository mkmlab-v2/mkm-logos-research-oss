#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-date directions from market_psych v2 + manifest (dna=0 default, B-track)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.market_psych_sasang_axis_v2 import (  # noqa: E402
    load_manifest,
    map_row_to_sasang,
    validate_psych_csv_fields,
)

DEFAULT_PSYCH = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"
DEFAULT_OUT = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--market-psych-csv", type=Path, default=DEFAULT_PSYCH)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--dna-weight", type=float, default=0.0)
    ap.add_argument("--market-weight", type=float, default=1.0)
    ap.add_argument("--neutral-band", type=float, default=0.06)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.market_psych_csv.is_file():
        print(f"missing {args.market_psych_csv}", file=sys.stderr)
        return 2

    manifest = load_manifest(args.manifest_json)
    rows_out: list[dict[str, Any]] = []
    prev_stress: float | None = None

    with args.market_psych_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        validate_psych_csv_fields(reader.fieldnames, manifest)
        for row in reader:
            ts = str(row.get("timestamp_utc") or "")[:10]
            if len(ts) != 10:
                continue
            mapped = map_row_to_sasang(
                row,
                manifest=manifest,
                neutral_band=args.neutral_band,
                prev_stress=prev_stress,
            )
            prev_stress = float(mapped["byungjeung"]["stress_index"])
            axis = mapped["axis_normalized"]
            rows_out.append(
                {
                    "eval_date": ts,
                    "instrument": "multi",
                    "predicted_direction": mapped["predicted_direction"],
                    "confidence": round(min(1.0, abs(mapped["fusion_direction_score"])), 6),
                    "ensemble_mode": "market_psych_sasang_v2",
                    "fusion_direction_score": mapped["fusion_direction_score"],
                    "mapping_target": mapped["mapping_target"],
                    "top_axis": mapped["top_axis"],
                    "fused_axis": axis,
                    "machine_readables": mapped["machine_readables"],
                    "byungjeung": mapped["byungjeung"],
                    "manifest_schema": manifest.get("schema"),
                    "manifest_version": manifest.get("version"),
                }
            )

    rows_out.sort(key=lambda r: r["eval_date"])
    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "ts_utc": _utc_now(),
        "ensemble_mode": "market_psych_sasang_v2",
        "fusion_rule": "market_psych v2 manifest axis_raw_weights; dna_weight=0 for index rail",
        "inputs": {
            "market_psych_csv": str(args.market_psych_csv.resolve()),
            "manifest_json": str(args.manifest_json.resolve()),
            "dna_weight": args.dna_weight,
            "market_weight": args.market_weight,
            "neutral_band": args.neutral_band,
        },
        "note": "B-track sandbox. Not AGCT cohort proxy. Not Track A.",
        "rows": rows_out,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE n_rows={len(rows_out)} path={args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
