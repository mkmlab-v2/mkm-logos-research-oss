#!/usr/bin/env python3
"""[HYPO] Multi-fold lens WF refit ablation — all folds gt margin summary (B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_multifold_refit_ablation_v1_latest.json"
WF = ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"

VARIANTS: list[dict[str, Any]] = [
    {"id": "baseline_bear_grid", "args": []},
    {"id": "source_direction_signal", "args": ["--include-source-direction-signal"]},
    {"id": "expanded_prior_features", "args": ["--include-expanded-prior-features"]},
    {
        "id": "source_and_expanded_prior",
        "args": ["--include-source-direction-signal", "--include-expanded-prior-features"],
    },
    {"id": "regime_min_w_cross", "args": ["--regime-adaptive-min-w-cross"]},
    {"id": "contrarian_guard", "args": ["--regime-adaptive-contrarian-guard"]},
    {"id": "train_min_w_cross_zero", "args": ["--train-min-w-cross", "0"]},
    {"id": "margin_vs_bull_objective", "args": ["--train-objective", "margin_vs_bull"]},
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fold_summaries(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for fold in doc.get("folds") or []:
        if not isinstance(fold, dict):
            continue
        test = fold.get("test") if isinstance(fold.get("test"), dict) else {}
        acc = float(test.get("accuracy") or 0.0)
        bull = float(test.get("always_bull_control") or 0.0)
        out.append(
            {
                "fold_index": int(fold.get("fold_index", -1)),
                "test_accuracy": round(acc, 6),
                "always_bull_control": round(bull, 6),
                "margin_vs_bull": round(acc - bull, 6),
                "gt_pass": acc > bull,
                "gte_pass": acc >= bull,
            }
        )
    return out


def _run_variant(
    *,
    score_json: Path,
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
        "--regime-adaptive-lens-features",
        "--regime-expanded-features-bull-min",
        "0.60",
        "--regime-expanded-features-bull-max",
        "0.625",
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
    folds = _fold_summaries(doc)
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    n_gt = sum(1 for f in folds if f.get("gt_pass"))
    row.update(
        {
            "folds": folds,
            "n_folds_gt_pass": n_gt,
            "n_folds_total": len(folds),
            "fraction_folds_gt_pass": round(n_gt / len(folds), 6) if folds else None,
            "mean_test_accuracy": agg.get("mean_test_accuracy"),
            "fraction_test_beats_always_bull_gt": agg.get("fraction_test_beats_always_bull"),
            "max_fold_margin_vs_bull": max((f.get("margin_vs_bull") or -999.0) for f in folds) if folds else None,
        }
    )
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tmp-dir", type=Path, default=ROOT / "reports/tmp_lens_multifold_refit_ablation")
    args = ap.parse_args()

    if not args.score_json.is_file():
        print(f"Missing score: {args.score_json}", file=sys.stderr)
        return 2

    args.tmp_dir.mkdir(parents=True, exist_ok=True)
    results = [
        _run_variant(
            score_json=args.score_json,
            n_folds=int(args.n_folds),
            variant_id=str(v["id"]),
            extra_args=list(v.get("args") or []),
            tmp_dir=args.tmp_dir,
        )
        for v in VARIANTS
    ]

    ok = [r for r in results if r.get("exit_code") == 0 and "fraction_folds_gt_pass" in r]
    best_gt = max(ok, key=lambda r: float(r.get("fraction_folds_gt_pass") or 0.0), default=None)
    best_margin = max(ok, key=lambda r: float(r.get("max_fold_margin_vs_bull") or -999.0), default=None)

    report: dict[str, Any] = {
        "schema": "prophecy_lens_multifold_refit_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {"score_json": str(args.score_json), "n_folds": int(args.n_folds), "n_variants": len(VARIANTS)},
        "best_by_fraction_folds_gt_pass": best_gt,
        "best_by_max_fold_margin": best_margin,
        "variants": results,
        "verdict_ko": (
            f"multifold refit; best_gt variant={(best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_folds_gt_pass')} — prod gate needs fraction>=0.5"
        ),
        "operator_lines": [
            "- [LENS-MFOLD] research_only; all WF folds per variant.",
            f"- [LENS-MFOLD] best_gt={(best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_folds_gt_pass')}.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
