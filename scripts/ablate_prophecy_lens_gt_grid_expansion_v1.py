#!/usr/bin/env python3
"""[HYPO] Lens WF grid/feature expansion ablation for strict gt beat-bull (B-track)."""
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
DEFAULT_OUT = ROOT / "reports/prophecy_lens_gt_grid_expansion_ablation_v1_latest.json"
WF = ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"

VARIANTS: list[dict[str, Any]] = [
    {"id": "prod_baseline_regime_adaptive", "args": []},
    {"id": "source_direction_signal", "args": ["--include-source-direction-signal"]},
    {"id": "expanded_prior_features", "args": ["--include-expanded-prior-features"]},
    {
        "id": "source_and_expanded_prior",
        "args": ["--include-source-direction-signal", "--include-expanded-prior-features"],
    },
    {
        "id": "wider_regime_band_055_070",
        "args": [
            "--regime-expanded-features-bull-min",
            "0.55",
            "--regime-expanded-features-bull-max",
            "0.70",
        ],
    },
    {
        "id": "contrarian_guard_margin_objective",
        "args": [
            "--regime-adaptive-contrarian-guard",
            "--train-objective",
            "margin_vs_bull",
            "--train-min-w-cross",
            "0",
        ],
    },
    {
        "id": "strict_first_min_margin_0p005",
        "args": ["--train-objective", "beat_bull_strict_first", "--train-min-margin-vs-bull", "0.005"],
    },
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
        "--target-instrument",
        "kospi",
        "--grid-profile",
        "kospi_bear_extended",
        "--regime-adaptive-lens-features",
        "--n-folds",
        str(n_folds),
        "--output",
        str(out),
    ]
    if "--regime-expanded-features-bull-min" not in extra_args:
        cmd.extend(["--regime-expanded-features-bull-min", "0.60", "--regime-expanded-features-bull-max", "0.625"])
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
    agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
    row.update(
        {
            "mean_test_accuracy": agg.get("mean_test_accuracy"),
            "fraction_test_beats_always_bull_gt": agg.get("fraction_test_beats_always_bull"),
            "fraction_test_meets_or_beats_always_bull_gte": agg.get("fraction_test_meets_or_beats_always_bull"),
        }
    )
    margins: list[float] = []
    for f in doc.get("folds") or []:
        if not isinstance(f, dict):
            continue
        t = f.get("test") if isinstance(f.get("test"), dict) else {}
        acc = float(t.get("accuracy") or 0.0)
        bull = float(t.get("always_bull_control") or 0.0)
        margins.append(round(acc - bull, 6))
    row["fold_margins_vs_prod_control"] = margins
    row["max_fold_margin_vs_prod_control"] = max(margins) if margins else None
    row["n_folds_exact_tie"] = sum(1 for m in margins if m == 0.0)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tmp-dir", type=Path, default=ROOT / "reports/tmp_lens_gt_grid_expansion_ablation")
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
        "schema": "prophecy_lens_gt_grid_expansion_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {"score_json": str(args.score_json), "n_folds": int(args.n_folds), "n_variants": len(VARIANTS)},
        "best_by_gt_fraction": best_gt,
        "best_by_max_fold_margin": best_margin,
        "variants": results,
        "verdict_ko": (
            "grid/feature expansion sweep; prod gt pass requires fraction_gt>0 — "
            + (
                f"best={best_gt.get('variant_id')} gt_frac={best_gt.get('fraction_test_beats_always_bull_gt')}"
                if best_gt
                else "no successful runs"
            )
        ),
        "operator_lines": [
            "- [LENS-GRID] research_only; prod comparator=gt unchanged.",
            f"- [LENS-GRID] best_gt variant={(best_gt or {}).get('variant_id')} "
            f"gt_frac={(best_gt or {}).get('fraction_test_beats_always_bull_gt')} "
            f"mean={(best_gt or {}).get('mean_test_accuracy')}.",
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
