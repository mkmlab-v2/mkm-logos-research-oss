#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-date price directions from DNA+market_psych fusion (B-track [HYPO])."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_sasang_dna_market_reasoning_v1 import (  # noqa: E402
    AXES,
    _build_market_axis_row,
    _normalize,
    _safe_float,
)

DEFAULT_PSYCH = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_latest.csv"
DEFAULT_OUT = ROOT / "reports/btrack_per_date_directions_agct_market_psych_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mapping_to_predicted(mt: str) -> str:
    m = str(mt or "").strip().lower()
    if m == "bull":
        return "bull"
    if m == "bear":
        return "bear"
    return "neutral"


def _direction_from_fused(fused: dict[str, float], neutral_band: float) -> tuple[str, float, str]:
    score = float(fused["TY"] + fused["SY"] - fused["TE"] - fused["SE"])
    if abs(score) < neutral_band:
        return "neutral", score, "sideways"
    if score > 0:
        return "bull", score, "bull"
    return "bear", score, "bear"


def _load_dna_axis(
    genotype_csv: Path,
    cohort_csv: Path | None,
    axis_weights_json: Path | None,
) -> dict[str, float]:
    proj_script = ROOT / "scripts/run_agct_sasang_composition_projection_v1.py"
    proj_out = ROOT / "reports/agct_sasang_composition_projection_per_date_v1.json"
    cmd = [
        sys.executable,
        str(proj_script),
        "--genotype-csv",
        str(genotype_csv),
        "--output-json",
        str(proj_out),
    ]
    if cohort_csv and cohort_csv.is_file():
        cmd.extend(["--cohort-csv", str(cohort_csv)])
    if axis_weights_json and axis_weights_json.is_file():
        cmd.extend(["--axis-weights-json", str(axis_weights_json)])
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        raise SystemExit(r.returncode)
    proj = json.loads(proj_out.read_text(encoding="utf-8"))
    return {
        a: _safe_float((proj.get("summary", {}).get("axis_summary", {}).get(a, {}) or {}).get("mean_projection"))
        for a in AXES
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--market-psych-csv", type=Path, default=DEFAULT_PSYCH)
    ap.add_argument("--genotype-csv", type=Path, default=ROOT / "tmp/bio_genotype_long_v1.csv")
    ap.add_argument("--cohort-csv", type=Path, default=ROOT / "tmp/bio_real_cohort_merged_with_sidecar_v1.csv")
    ap.add_argument(
        "--axis-weights-json",
        type=Path,
        default=ROOT / "tmp/agct_sasang_axis_weights_active_btrack_v1.json",
    )
    ap.add_argument(
        "--dna-weight",
        type=float,
        default=0.0,
        help="Market price per-date rail: 0 = no cohort DNA prior (human rail separate).",
    )
    ap.add_argument(
        "--market-weight",
        type=float,
        default=1.0,
        help="Market psych row weight for index direction (default 1.0).",
    )
    ap.add_argument("--neutral-band", type=float, default=0.06)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.market_psych_csv.is_file():
        print(f"missing {args.market_psych_csv}", file=sys.stderr)
        return 2

    dna_axis = _normalize(_load_dna_axis(args.genotype_csv, args.cohort_csv, args.axis_weights_json))

    rows_out: list[dict[str, Any]] = []
    with args.market_psych_csv.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ts = str(row.get("timestamp_utc") or "")[:10]
            if len(ts) != 10:
                continue
            market_axis, metrics = _build_market_axis_row(row)
            fused = _normalize(
                {
                    a: args.dna_weight * dna_axis[a] + args.market_weight * market_axis[a]
                    for a in AXES
                }
            )
            pred, score, mt = _direction_from_fused(fused, args.neutral_band)
            top = max(AXES, key=lambda a: fused[a])
            rows_out.append(
                {
                    "eval_date": ts,
                    "instrument": "multi",
                    "predicted_direction": pred,
                    "confidence": round(min(1.0, abs(score)), 6),
                    "ensemble_mode": "agct_market_psych_fusion_v1",
                    "fusion_direction_score": round(score, 6),
                    "mapping_target": mt,
                    "top_axis": top,
                    "fused_axis": {k: round(fused[k], 6) for k in AXES},
                    "market_metrics": metrics,
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
        "ensemble_mode": "agct_market_psych_fusion_v1",
        "fusion_rule": "fused = normalize(dna_weight*dna + market_weight*market_psych_row); direction from (TY+SY)-(TE+SE)",
        "inputs": {
            "market_psych_csv": str(args.market_psych_csv.resolve()),
            "dna_weight": args.dna_weight,
            "market_weight": args.market_weight,
            "neutral_band": args.neutral_band,
        },
        "note": "Use with build_btrack_prophecy_score_from_ohlcv.py --per-date-direction-json. Not AGCT external_proxy_accuracy.",
        "rows": rows_out,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE n_rows={len(rows_out)} path={args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
