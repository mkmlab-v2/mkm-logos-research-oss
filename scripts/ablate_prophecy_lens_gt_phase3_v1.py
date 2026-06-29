#!/usr/bin/env python3
"""[HYPO] Phase3 lens gt R&D — architecture beyond grid + regime-conditional train paths."""
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
DEFAULT_OUT = ROOT / "reports/prophecy_lens_gt_phase3_ablation_v1_latest.json"
WF = ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"

COMMON = [
    "--target-instrument",
    "kospi",
    "--grid-profile",
    "kospi_bear_extended",
    "--regime-adaptive-lens-features",
    "--regime-expanded-features-bull-min",
    "0.60",
    "--regime-expanded-features-bull-max",
    "0.625",
]

VARIANTS: list[dict[str, Any]] = [
    {"id": "prod_beat_bull_first_baseline", "args": ["--train-objective", "beat_bull_first"]},
    {"id": "train_objective_accuracy", "args": ["--train-objective", "accuracy"]},
    {"id": "train_objective_margin_vs_bull", "args": ["--train-objective", "margin_vs_bull"]},
    {
        "id": "regime_adaptive_bull_train_beat_bull",
        "args": [
            "--regime-adaptive-bull-train",
            "--regime-bull-train-floor",
            "0.55",
            "--train-objective",
            "beat_bull_first",
        ],
    },
    {
        "id": "regime_adaptive_bull_train_accuracy",
        "args": [
            "--regime-adaptive-bull-train",
            "--regime-bull-train-floor",
            "0.55",
            "--train-objective",
            "accuracy",
        ],
    },
    {
        "id": "regime_lookback_20_margin",
        "args": [
            "--regime-adaptive-lookback-days",
            "20",
            "--train-objective",
            "margin_vs_bull",
        ],
    },
    {"id": "regime_adaptive_min_w_cross", "args": ["--regime-adaptive-min-w-cross"]},
    {"id": "bear_day_weighted_first", "args": ["--train-objective", "bear_day_weighted_first"]},
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        *COMMON,
        "--n-folds",
        str(n_folds),
        "--output",
        str(out),
        *extra_args,
    ]
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
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    margins: list[float] = []
    for f in doc.get("folds") or []:
        if not isinstance(f, dict):
            continue
        t = f.get("test") if isinstance(f.get("test"), dict) else {}
        acc = float(t.get("accuracy") or 0.0)
        bull = float(t.get("always_bull_control") or 0.0)
        margins.append(round(acc - bull, 6))
    row.update(
        {
            "mean_test_accuracy": agg.get("mean_test_accuracy"),
            "fraction_test_beats_always_bull_gt": agg.get("fraction_test_beats_always_bull"),
            "fraction_test_meets_or_beats_always_bull_gte": agg.get("fraction_test_meets_or_beats_always_bull"),
            "fold_margins_vs_prod_control": margins,
            "max_fold_margin_vs_prod_control": max(margins) if margins else None,
            "n_folds_exact_tie": sum(1 for m in margins if m == 0.0),
            "n_folds_gt_pass": sum(1 for m in margins if m > 0.0),
        }
    )
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tmp-dir", type=Path, default=ROOT / "reports/tmp_lens_gt_phase3_ablation")
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

    ok = [r for r in results if r.get("exit_code") == 0 and "mean_test_accuracy" in r]
    best_gt = max(ok, key=lambda r: float(r.get("fraction_test_beats_always_bull_gt") or 0.0), default=None)
    best_margin = max(ok, key=lambda r: float(r.get("max_fold_margin_vs_prod_control") or -999.0), default=None)

    report: dict[str, Any] = {
        "schema": "prophecy_lens_gt_phase3_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "phase": "3_architecture_and_regime_conditional_train",
        "inputs": {"score_json": str(args.score_json), "n_folds": int(args.n_folds), "n_variants": len(VARIANTS)},
        "best_by_gt_fraction": best_gt,
        "best_by_max_fold_margin": best_margin,
        "variants": results,
        "verdict_ko": (
            f"phase3 architecture; best_gt={(best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_test_beats_always_bull_gt')} "
            f"max_margin={(best_gt or {}).get('max_fold_margin_vs_prod_control')}"
        ),
        "ledger_line": (
            f"Lens gt phase3: best_gt={(best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_test_beats_always_bull_gt')} "
            f"mean={(best_gt or {}).get('mean_test_accuracy')}; prod gt unchanged; no oper promotion."
        ),
        "operator_lines": [
            "- [LENS-P3] research_only; architecture + regime-conditional train paths.",
            f"- [LENS-P3] best_gt={(best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_test_beats_always_bull_gt')} "
            f"ties={(best_gt or {}).get('n_folds_exact_tie')}.",
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
