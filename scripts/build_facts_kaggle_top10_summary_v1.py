#!/usr/bin/env python3
"""Build compact JSON summary from FACTS eval-vs-Kaggle report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _avg_score(row: dict[str, Any]) -> float | None:
    scores = row.get("scores") or {}
    avg = scores.get("Average") or {}
    val = avg.get("score")
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build FACTS Kaggle top10 compact summary JSON.")
    ap.add_argument(
        "--in-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_eval_vs_kaggle_report_latest.json"),
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_kaggle_top10_summary_latest.json"),
    )
    ap.add_argument("--top-n", type=int, default=10)
    args = ap.parse_args()

    body = json.loads(args.in_json.read_text(encoding="utf-8"))
    top = (body.get("kaggle_top_models") or [])[: max(0, args.top_n)]
    internal_metrics = (body.get("internal_eval") or {}).get("metrics") or {}
    side = body.get("side_by_side") or {}
    matched = (side.get("kaggle_model") or {}) if isinstance(side, dict) else {}

    compact_top = []
    for row in top:
        compact_top.append(
            {
                "rank": row.get("rank"),
                "display_name": row.get("display_name"),
                "organization": row.get("organization"),
                "model_proxy_slug": row.get("model_proxy_slug"),
                "average_score": _avg_score(row),
            }
        )

    out = {
        "schema": "facts_kaggle_top_summary_v1",
        "generated_at_utc": _now_utc_iso(),
        "source_report": str(args.in_json),
        "internal_metrics": {
            "coverage": internal_metrics.get("coverage"),
            "answered_accuracy": internal_metrics.get("answered_accuracy"),
            "hold_rate": internal_metrics.get("hold_rate"),
            "unknown_hold_rate": internal_metrics.get("unknown_hold_rate"),
        },
        "matched_model": {
            "display_name": matched.get("display_name"),
            "rank": matched.get("rank"),
            "kaggle_average_score": matched.get("kaggle_average_score"),
        },
        "kaggle_top_models_compact": compact_top,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {args.out_json}")
    print(f"[SUMMARY] top_n={len(compact_top)}, matched_rank={out['matched_model']['rank']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
