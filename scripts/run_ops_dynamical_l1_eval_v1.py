#!/usr/bin/env python3
"""Ops dynamical L1 — 10m horizon stage prediction ε from JSONL timeseries [HYPO · B-track]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_dynamical_bench_v1_lib import (  # noqa: E402
    DEFAULT_HORIZON_MINUTES,
    DEFAULT_JSONL,
    DEFAULT_OUT,
    build_report,
    eval_l1_pairs,
    read_jsonl,
)

OUT = ROOT / "reports/ops_dynamical_l1_eval_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate ops dynamical L1 prediction pairs")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--horizon-minutes", type=float, default=DEFAULT_HORIZON_MINUTES)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--patch-bench-latest", action="store_true", default=True)
    parser.add_argument("--no-patch-bench-latest", dest="patch_bench_latest", action="store_false")
    args = parser.parse_args()

    rows = read_jsonl(args.jsonl)
    doc = eval_l1_pairs(rows, horizon_minutes=args.horizon_minutes)
    doc["jsonl_path"] = str(args.jsonl).replace("\\", "/")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.patch_bench_latest and doc["pairs_evaluated"] > 0:
        latest = build_report(fractal_level="L1_prediction")
        last_pair = next(p for p in reversed(doc["pairs"]) if p["status"] == "evaluated")
        latest["validation"] = {
            "observed_stage": last_pair.get("observed_stage"),
            "timing_error_minutes": last_pair.get("timing_error_minutes"),
            "intervention_applied": False,
            "intervention_ok": None,
            "stage_exact_match": last_pair.get("stage_exact_match"),
            "stage_rank_delta": last_pair.get("stage_rank_delta"),
        }
        latest["fractal_level"] = "L1_prediction"
        DEFAULT_OUT.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "pairs_evaluated": doc["pairs_evaluated"],
                "stage_exact_match_rate": doc["metrics"]["stage_exact_match_rate"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
