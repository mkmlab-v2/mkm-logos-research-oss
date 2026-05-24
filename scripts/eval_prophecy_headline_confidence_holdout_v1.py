#!/usr/bin/env python3
"""Temporal holdout for min-confidence ACTIVE hit-rate gate (O-P28 B-track).

Train: pick min_confidence on first date fraction. Test: report active hit rate on held-out dates.
Does not overwrite headline eval or enable live trading.
"""
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

from scripts.sweep_prophecy_headline_deadzone_hold_v1 import (
    SCHEMA as SWEEP_SCHEMA,
    _load_json,
    _lookup_per_date_meta,
    _metrics_active,
    _metrics_all,
    _per_date_index,
)

DEFAULT_SCORE = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_PER_DATE = ROOT / "reports" / "btrack_ensemble_per_date_directions_180d_v1_latest.json"
DEFAULT_OUT = ROOT / "reports" / "prophecy_headline_confidence_holdout_v1_latest.json"
SCHEMA = "prophecy_headline_confidence_holdout_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _split_rows_by_date(
    rows: list[dict[str, Any]],
    *,
    train_fraction: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[str]]:
    dates = sorted({str(r.get("eval_date") or "")[:10] for r in rows if r.get("eval_date")})
    if not dates:
        return [], [], [], []
    n_train = max(1, int(len(dates) * train_fraction))
    if n_train >= len(dates):
        n_train = max(1, len(dates) - 1)
    train_dates = set(dates[:n_train])
    test_dates = set(dates[n_train:])
    train_rows = [r for r in rows if str(r.get("eval_date") or "")[:10] in train_dates]
    test_rows = [r for r in rows if str(r.get("eval_date") or "")[:10] in test_dates]
    return train_rows, test_rows, sorted(train_dates), sorted(test_dates)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--per-date-json", type=Path, default=DEFAULT_PER_DATE)
    ap.add_argument("--train-fraction", type=float, default=0.5)
    ap.add_argument(
        "--min-confidence-grid",
        type=str,
        default="0.0,0.15,0.18,0.20,0.22,0.25,0.30",
    )
    ap.add_argument("--score-abs-deadzone", type=float, default=0.0)
    ap.add_argument("--min-coverage-active", type=float, default=0.50)
    ap.add_argument("--min-test-hit-rate", type=float, default=0.50)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score_doc = _load_json(args.score_json)
    if not score_doc or not isinstance(score_doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {args.score_json}")
    rows = [r for r in score_doc["rows"] if isinstance(r, dict)]
    pdx = _per_date_index(args.per_date_json)
    train_rows, test_rows, train_dates, test_dates = _split_rows_by_date(
        rows, train_fraction=float(args.train_fraction)
    )
    if not train_rows or not test_rows:
        raise SystemExit("insufficient dates for holdout split")

    conf_grid = [float(x.strip()) for x in args.min_confidence_grid.split(",") if x.strip()]
    score_dz = float(args.score_abs_deadzone)

    train_candidates: list[dict[str, Any]] = []
    for min_conf in conf_grid:
        m = _metrics_active(
            train_rows,
            min_confidence=min_conf,
            score_abs_deadzone=score_dz,
            per_date_index=pdx,
        )
        cov = float(m.get("coverage_active") or 0.0)
        rate = float(m.get("price_directional_hit_rate_active") or 0.0)
        train_candidates.append(
            {
                "min_confidence": min_conf,
                "metrics": m,
                "passes_coverage_floor": cov >= float(args.min_coverage_active),
            }
        )
    train_ranked = sorted(
        train_candidates,
        key=lambda x: (
            1 if x.get("passes_coverage_floor") else 0,
            float((x.get("metrics") or {}).get("price_directional_hit_rate_active") or -1.0),
        ),
        reverse=True,
    )
    best_train = train_ranked[0] if train_ranked else None
    chosen_conf = float(best_train["min_confidence"]) if best_train else 0.18

    test_metrics = _metrics_active(
        test_rows,
        min_confidence=chosen_conf,
        score_abs_deadzone=score_dz,
        per_date_index=pdx,
    )
    test_all = _metrics_all(test_rows)
    full_all = _metrics_all(rows)
    test_rate = float(test_metrics.get("price_directional_hit_rate_active") or 0.0)
    test_cov = float(test_metrics.get("coverage_active") or 0.0)
    holdout_ok = test_rate >= float(args.min_test_hit_rate) and test_cov >= float(args.min_coverage_active)

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "boundary_ack": True,
        "inputs": {
            "score_json": str(args.score_json),
            "per_date_json": str(args.per_date_json),
            "train_fraction": float(args.train_fraction),
            "train_dates": train_dates,
            "test_dates": test_dates,
            "min_confidence_grid": conf_grid,
            "score_abs_deadzone": score_dz,
            "min_test_hit_rate": float(args.min_test_hit_rate),
            "min_coverage_active": float(args.min_coverage_active),
            "sweep_schema_ref": SWEEP_SCHEMA,
        },
        "baseline_all_panel": full_all,
        "train": {
            "best_on_train": best_train,
            "top_on_train": train_ranked[:5],
            "chosen_min_confidence": chosen_conf,
        },
        "test": {
            "metrics_active": test_metrics,
            "metrics_all": test_all,
            "holdout_pass": holdout_ok,
        },
        "promotion_shadow_allowed": holdout_ok,
        "note": (
            "holdout_pass only allows shadow score path under reports/; "
            "does not mutate docs/final/artifacts/prophecy_hit_rate_eval_latest.json."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"chosen_conf={chosen_conf} TEST_ACTIVE={test_rate} cov={test_cov} "
        f"holdout_pass={holdout_ok}"
    )
    return 0 if holdout_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
