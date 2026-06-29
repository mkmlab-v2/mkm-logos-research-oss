# @MKM12-METADATA
# Type: Logic
# Purpose: Fold-targeted lens WF refit ablation (B-track research)
# Keywords: prophecy, fold, ablation, lens, beat_bull
#!/usr/bin/env python3
"""Sweep lens walk-forward variants and report one fold's test metrics.

B-track / [HYPO] / research_only — does not change production gates automatically.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports" / "prophecy_lens_fold_refit_ablation_v1_latest.json"
WF = ROOT / "scripts" / "run_prophecy_per_date_combo_walkforward_v1.py"

VARIANTS: list[dict[str, Any]] = [
    {"id": "baseline_bear_grid", "args": []},
    {"id": "source_direction_signal", "args": ["--include-source-direction-signal"]},
    {"id": "expanded_prior_features", "args": ["--include-expanded-prior-features"]},
    {"id": "source_and_expanded_prior", "args": ["--include-source-direction-signal", "--include-expanded-prior-features"]},
    {"id": "regime_min_w_cross", "args": ["--regime-adaptive-min-w-cross"]},
    {"id": "contrarian_guard", "args": ["--regime-adaptive-contrarian-guard"]},
    {"id": "train_min_w_cross_zero", "args": ["--train-min-w-cross", "0"]},
    {"id": "margin_vs_bull_objective", "args": ["--train-objective", "margin_vs_bull"]},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fold_row(doc: dict[str, Any], fold_index: int) -> dict[str, Any] | None:
    for f in doc.get("folds") or []:
        if isinstance(f, dict) and int(f.get("fold_index", -1)) == fold_index:
            return f
    return None


def _run_variant(
    *,
    score_json: Path,
    fold_index: int,
    n_folds: int,
    variant_id: str,
    extra_args: list[str],
    tmp_dir: Path,
) -> dict[str, Any]:
    out = tmp_dir / f"wf_{variant_id}.json"
    cmd = [
        sys.executable,
        str(WF),
        "--score-json",
        str(score_json),
        "--target-instrument",
        "kospi",
        "--grid-profile",
        "kospi_bear_extended",
        "--n-folds",
        str(n_folds),
        "--output",
        str(out),
    ]
    if "--train-objective" not in extra_args:
        cmd.extend(["--train-objective", "beat_bull_first"])
    cmd.extend(extra_args)

    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    row: dict[str, Any] = {
        "variant_id": variant_id,
        "exit_code": int(proc.returncode),
        "cmd": cmd,
        "walkforward_json": str(out),
    }
    if proc.returncode != 0:
        row["stderr_tail"] = (proc.stderr or "")[-2000:]
        return row
    if not out.is_file():
        row["error"] = "missing_output"
        return row
    doc = json.loads(out.read_text(encoding="utf-8"))
    fold = _fold_row(doc, fold_index)
    if not fold:
        row["error"] = "fold_not_found"
        return row
    test = fold.get("test") if isinstance(fold.get("test"), dict) else {}
    acc = float(test.get("accuracy") or 0.0)
    bull = float(test.get("always_bull_control") or 0.0)
    row.update(
        {
            "fold_index": fold_index,
            "test_accuracy": round(acc, 6),
            "always_bull_control": round(bull, 6),
            "margin_vs_bull": round(acc - bull, 6),
            "gt_pass": acc > bull,
            "gte_pass": acc >= bull,
            "best_params_from_train": fold.get("best_params_from_train"),
            "train_objective_effective": fold.get("train_objective_effective"),
        }
    )
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    row["full_panel_fraction_test_beats_always_bull"] = agg.get("fraction_test_beats_always_bull")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="Fold-targeted lens WF variant ablation.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--fold-index", type=int, default=1)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tmp-dir", type=Path, default=ROOT / "reports" / "tmp_lens_fold_refit_ablation")
    args = ap.parse_args()

    if not args.score_json.is_file():
        print(f"Missing score: {args.score_json}", file=sys.stderr)
        return 2
    if not WF.is_file():
        print(f"Missing WF script: {WF}", file=sys.stderr)
        return 2

    args.tmp_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for v in VARIANTS:
        results.append(
            _run_variant(
                score_json=args.score_json,
                fold_index=int(args.fold_index),
                n_folds=int(args.n_folds),
                variant_id=str(v["id"]),
                extra_args=list(v.get("args") or []),
                tmp_dir=args.tmp_dir,
            )
        )

    ok_rows = [r for r in results if r.get("exit_code") == 0 and "test_accuracy" in r]
    best_gt = max(ok_rows, key=lambda r: (bool(r.get("gt_pass")), float(r.get("test_accuracy") or 0.0)), default=None)
    best_margin = max(ok_rows, key=lambda r: float(r.get("margin_vs_bull") or -999.0), default=None)

    out_doc: dict[str, Any] = {
        "schema": "prophecy_lens_fold_refit_ablation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "fold_index": int(args.fold_index),
            "n_folds": int(args.n_folds),
            "n_variants": len(VARIANTS),
        },
        "best_by_gt_pass_then_accuracy": best_gt,
        "best_by_margin_vs_bull": best_margin,
        "variants": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if best_gt:
        print(
            f"best_gt variant={best_gt.get('variant_id')} acc={best_gt.get('test_accuracy')} "
            f"bull={best_gt.get('always_bull_control')} gt_pass={best_gt.get('gt_pass')}"
        )
    return 0 if ok_rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
