#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_WF_SCRIPT = ROOT / "scripts" / "run_prophecy_per_date_combo_walkforward_v1.py"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_btc_promotion_search_v1_latest.json"
SCHEMA = "prophecy_btc_promotion_search_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_cmd(args: list[str]) -> tuple[int, str]:
    p = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return p.returncode, (p.stdout + "\n" + p.stderr).strip()


def _passes(agg: dict[str, Any], *, min_mean: float, max_stdev: float, min_beat: float, min_fold: float) -> bool:
    return (
        float(agg.get("mean_test_accuracy") or 0.0) >= min_mean
        and float(agg.get("stdev_test_accuracy") or 0.0) <= max_stdev
        and float(agg.get("fraction_test_beats_always_bull") or 0.0) >= min_beat
        and float(agg.get("min_test_accuracy") or 0.0) >= min_fold
    )


def _score(agg: dict[str, Any]) -> float:
    mean_v = float(agg.get("mean_test_accuracy") or 0.0)
    stdev_v = float(agg.get("stdev_test_accuracy") or 0.0)
    beat_v = float(agg.get("fraction_test_beats_always_bull") or 0.0)
    min_v = float(agg.get("min_test_accuracy") or 0.0)
    return (2.0 * mean_v) + (1.2 * beat_v) + (0.8 * min_v) - stdev_v


def main() -> int:
    ap = argparse.ArgumentParser(description="Search BTC walk-forward promotion candidates.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--wf-script", type=Path, default=DEFAULT_WF_SCRIPT)
    ap.add_argument("--n-folds-grid", type=str, default="4,5,6,8,10")
    ap.add_argument("--objective-grid", type=str, default="margin_vs_bull,accuracy")
    ap.add_argument("--min-mean", type=float, default=0.55)
    ap.add_argument("--max-stdev", type=float, default=0.15)
    ap.add_argument("--min-beat-bull-frac", type=float, default=0.5)
    ap.add_argument("--min-worst-fold", type=float, default=0.4)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.wf_script.is_file():
        raise SystemExit(f"missing walkforward script: {args.wf_script}")

    n_folds_grid = [int(x.strip()) for x in args.n_folds_grid.split(",") if x.strip()]
    objective_grid = [x.strip() for x in args.objective_grid.split(",") if x.strip()]
    combos = list(itertools.product(n_folds_grid, objective_grid))

    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for n_folds, objective in combos:
        with tempfile.NamedTemporaryFile(prefix="btc_wf_", suffix=".json", delete=False) as tf:
            tmp_out = Path(tf.name)
        cmd = [
            sys.executable,
            str(args.wf_script),
            "--score-json",
            str(args.score_json),
            "--target-instrument",
            "btc",
            "--train-objective",
            objective,
            "--n-folds",
            str(n_folds),
            "--output",
            str(tmp_out),
        ]
        code, log = _run_cmd(cmd)
        if code != 0:
            errors.append({"n_folds": n_folds, "train_objective": objective, "error": log[:1200]})
            continue
        try:
            doc = json.loads(tmp_out.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            errors.append({"n_folds": n_folds, "train_objective": objective, "error": f"invalid_json: {e}"})
            continue
        agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
        candidates.append(
            {
                "n_folds": n_folds,
                "train_objective": objective,
                "aggregate": agg,
                "passes_default_gates": _passes(
                    agg,
                    min_mean=args.min_mean,
                    max_stdev=args.max_stdev,
                    min_beat=args.min_beat_bull_frac,
                    min_fold=args.min_worst_fold,
                ),
                "rank_score": round(_score(agg), 6),
            }
        )

    ranked = sorted(candidates, key=lambda c: (bool(c["passes_default_gates"]), float(c["rank_score"])), reverse=True)
    passed = [c for c in ranked if c.get("passes_default_gates")]

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "n_folds_grid": n_folds_grid,
            "objective_grid": objective_grid,
            "thresholds": {
                "min_mean_test_accuracy": args.min_mean,
                "max_stdev_test_accuracy": args.max_stdev,
                "min_fraction_test_beats_always_bull": args.min_beat_bull_frac,
                "min_min_test_accuracy_across_folds": args.min_worst_fold,
            },
            "total_candidates": len(combos),
        },
        "summary": {
            "n_successful_runs": len(candidates),
            "n_failed_runs": len(errors),
            "n_pass_candidates": len(passed),
            "best_candidate": ranked[0] if ranked else None,
        },
        "top_candidates": ranked[: max(1, int(args.top_k))],
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"runs={len(candidates)} pass={len(passed)} fail={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

