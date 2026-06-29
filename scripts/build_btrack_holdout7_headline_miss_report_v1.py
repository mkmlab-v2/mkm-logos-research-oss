#!/usr/bin/env python3
"""[HYPO] Holdout7-only headline miss report from 180d per-date (04-02 neutral_miss lane)."""
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

from scripts.build_btrack_holdout7_uncovered_four_probe_v1 import _prepare_rows
from scripts.btrack_wrong_dir_holdout_core_v1 import holdout_dates_from_cf

DEFAULT_CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
DEFAULT_PER = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"
DEFAULT_DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_holdout7_headline_miss_report_v1_latest.json"


def build_report(per_doc: dict[str, Any], holdout: list[str], dump: dict[str, Any]) -> dict[str, Any]:
    by_date = _prepare_rows(per_doc, holdout, dump)
    misses: list[dict[str, Any]] = []
    hits = 0
    for ed in holdout:
        row = by_date.get(ed) or {}
        pred = str(row.get("predicted_direction") or "").lower()
        act = str(row.get("actual_direction") or "").lower()
        if not act:
            continue
        if pred == act:
            hits += 1
        else:
            kind = "neutral_abstain_miss" if pred == "neutral" else "wrong_direction"
            misses.append(
                {
                    "eval_date": ed,
                    "predicted_direction": pred,
                    "actual_direction": act,
                    "miss_kind": kind,
                    "confidence": row.get("confidence"),
                    "preliminary_direction": row.get("preliminary_direction"),
                }
            )
    n = hits + len(misses)
    return {
        "schema": "btrack_holdout7_headline_miss_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panel": "holdout7_btc_180d_per_date",
        "holdout_dates": holdout,
        "n_evaluated": n,
        "price_hits": hits,
        "price_directional_hit_rate": round(hits / n, 6) if n else None,
        "n_misses": len(misses),
        "miss_breakdown": {
            "wrong_direction": sum(1 for m in misses if m["miss_kind"] == "wrong_direction"),
            "neutral_abstain_miss": sum(1 for m in misses if m["miss_kind"] == "neutral_abstain_miss"),
        },
        "misses": misses,
        "operator_line": (
            f"- [MKM-HOLDOUT7-MISS] {hits}/{n} hits; "
            f"wrong_dir={sum(1 for m in misses if m['miss_kind']=='wrong_direction')} "
            f"neutral_miss={sum(1 for m in misses if m['miss_kind']=='neutral_abstain_miss')}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--counterfactual", type=Path, default=DEFAULT_CF)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER)
    ap.add_argument("--feature-dump", type=Path, default=DEFAULT_DUMP)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.per_date_json.is_file() or not args.feature_dump.is_file():
        print(f"Missing per-date or dump: {args.per_date_json} {args.feature_dump}", file=sys.stderr)
        return 2
    holdout = holdout_dates_from_cf(args.counterfactual)
    report = build_report(
        json.loads(args.per_date_json.read_text(encoding="utf-8")),
        holdout,
        json.loads(args.feature_dump.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(report["operator_line"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
