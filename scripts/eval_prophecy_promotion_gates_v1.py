# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.84, K:0.48, M:0.34}
# Balance: 90
# Purpose: B-track numeric gates before any prophecy feature promotion
# Keywords: prophecy, promotion, gates, walkforward, hypos
#!/usr/bin/env python3
"""Numeric promotion gates for B-track prophecy (measurement-only).

Reads ``prophecy_per_date_combo_walkforward_v1_latest.json`` aggregate + folds,
optionally checks ``btrack_prophecy_score_latest.json`` for KOSPI+BTC panel completeness.

This script does **not** change routing, weights, or live trading. It only emits a
pass/fail report. Use ``--fail-on-gate`` in CI to block merges when gates fail.

Default thresholds are conservative; tune via CLI flags after team agreement.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WALKFORWARD = ROOT / "docs" / "final" / "artifacts" / "prophecy_per_date_combo_walkforward_v1_latest.json"
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_promotion_gates_v1_latest.json"
SCHEMA = "prophecy_promotion_gates_v1"
VALID_DIR = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _panel_dual_leg_gate(score_path: Path) -> dict[str, Any]:
    doc = _load_json(score_path)
    if not doc or not isinstance(doc.get("rows"), list):
        return {
            "gate_id": "panel_kospi_btc_per_date",
            "passed": False,
            "reason": "missing_or_invalid_score_json",
            "detail": {},
        }
    rows = [r for r in doc["rows"] if isinstance(r, dict)]
    by_date: dict[str, set[str]] = {}
    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        inst = str(r.get("instrument") or "").strip().lower()
        act = str(r.get("actual_direction") or "").strip().lower()
        if not ed or inst not in ("kospi", "btc") or act not in VALID_DIR:
            continue
        by_date.setdefault(ed, set()).add(inst)
    complete_dates = [d for d, legs in sorted(by_date.items()) if legs >= {"kospi", "btc"}]
    n_dates = len(by_date)
    n_complete = len(complete_dates)
    passed = n_complete == n_dates and n_dates > 0
    return {
        "gate_id": "panel_kospi_btc_per_date",
        "passed": passed,
        "reason": None if passed else "each_eval_date_must_have_kospi_and_btc_with_valid_actuals",
        "detail": {
            "n_eval_dates_with_any_row": n_dates,
            "n_eval_dates_with_kospi_and_btc": n_complete,
            "n_score_rows": len(rows),
        },
    }


def _walkforward_gates(wf: dict[str, Any], *, min_mean: float, max_stdev: float, min_beat_frac: float, min_worst_fold: float) -> list[dict[str, Any]]:
    agg = wf.get("aggregate") if isinstance(wf.get("aggregate"), dict) else {}
    folds = wf.get("folds") if isinstance(wf.get("folds"), list) else []

    mean_v = float(agg.get("mean_test_accuracy") or 0.0)
    stdev_v = float(agg.get("stdev_test_accuracy") or 0.0)
    beat_v = float(agg.get("fraction_test_beats_always_bull") or 0.0)
    min_fold = float(agg.get("min_test_accuracy") or 0.0)

    gates: list[dict[str, Any]] = [
        {
            "gate_id": "wf_mean_test_accuracy",
            "passed": mean_v >= min_mean,
            "threshold": {"op": ">=", "min_mean_test_accuracy": min_mean},
            "observed": {"mean_test_accuracy": round(mean_v, 6)},
        },
        {
            "gate_id": "wf_stdev_test_accuracy",
            "passed": stdev_v <= max_stdev,
            "threshold": {"op": "<=", "max_stdev_test_accuracy": max_stdev},
            "observed": {"stdev_test_accuracy": round(stdev_v, 6)},
        },
        {
            "gate_id": "wf_fraction_folds_beat_always_bull",
            "passed": beat_v >= min_beat_frac,
            "threshold": {"op": ">=", "min_fraction_test_beats_always_bull": min_beat_frac},
            "observed": {"fraction_test_beats_always_bull": round(beat_v, 6), "n_folds": len(folds)},
        },
        {
            "gate_id": "wf_min_fold_test_accuracy",
            "passed": min_fold >= min_worst_fold,
            "threshold": {"op": ">=", "min_min_test_accuracy_across_folds": min_worst_fold},
            "observed": {"min_test_accuracy": round(min_fold, 6)},
        },
    ]
    return gates


def main() -> int:
    ap = argparse.ArgumentParser(description="B-track prophecy promotion numeric gates (report only).")
    ap.add_argument("--walkforward-json", type=Path, default=DEFAULT_WALKFORWARD)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE, help="If present, require KOSPI+BTC per eval_date.")
    ap.add_argument("--skip-panel-gate", action="store_true", help="Do not load score JSON for dual-leg check.")
    ap.add_argument("--min-mean", type=float, default=0.55, dest="min_mean")
    ap.add_argument("--max-stdev", type=float, default=0.15, dest="max_stdev")
    ap.add_argument("--min-beat-bull-frac", type=float, default=0.5, dest="min_beat_frac")
    ap.add_argument("--min-worst-fold", type=float, default=0.4, dest="min_worst_fold")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--fail-on-gate", action="store_true", help="Exit 1 if any gate fails.")
    args = ap.parse_args()

    wf = _load_json(args.walkforward_json) or {}
    if str(wf.get("schema") or "") != "prophecy_per_date_combo_walkforward_v1":
        out_err = {
            "schema": SCHEMA,
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "promotion_recommendation": "defer",
            "all_gates_passed": False,
            "error": f"missing_or_invalid_walkforward: {args.walkforward_json}",
        }
        text = json.dumps(out_err, ensure_ascii=False, indent=2) + "\n"
        print(text)
        if not args.stdout_only:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        return 1 if args.fail_on_gate else 0

    wf_gates = _walkforward_gates(
        wf,
        min_mean=args.min_mean,
        max_stdev=args.max_stdev,
        min_beat_frac=args.min_beat_frac,
        min_worst_fold=args.min_worst_fold,
    )
    gates: list[dict[str, Any]] = list(wf_gates)

    if not args.skip_panel_gate and args.score_json.is_file():
        gates.append(_panel_dual_leg_gate(args.score_json))

    all_passed = all(bool(g.get("passed")) for g in gates)
    recommendation = "manual_review_candidate" if all_passed else "defer"

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "walkforward_json": str(args.walkforward_json),
            "score_json": str(args.score_json) if not args.skip_panel_gate else None,
            "thresholds": {
                "min_mean_test_accuracy": args.min_mean,
                "max_stdev_test_accuracy": args.max_stdev,
                "min_fraction_test_beats_always_bull": args.min_beat_frac,
                "min_min_test_accuracy_across_folds": args.min_worst_fold,
            },
            "skip_panel_gate": bool(args.skip_panel_gate),
        },
        "gates": gates,
        "all_gates_passed": all_passed,
        "promotion_recommendation": recommendation,
        "note": "Conservative B-track gates only; human sign-off still required before any A-track or live routing change.",
    }

    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")

    if args.fail_on_gate and not all_passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
