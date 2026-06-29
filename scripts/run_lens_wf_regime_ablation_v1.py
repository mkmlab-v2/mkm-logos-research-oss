#!/usr/bin/env python3
"""[HYPO] Grid of lens walk-forward variants — research_only summary JSON."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "reports/prophecy_btrack_recommended_nbps_sweep_v1/btrack_prophecy_score_recommended_nbps_2_0.json"
DEFAULT_OUT = ROOT / "reports/lens_wf_regime_ablation_v1_latest.json"
WF = ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"

VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline_margin_btc_nf6", "args": ["--target-instrument", "btc", "--train-objective", "margin_vs_bull", "--n-folds", "6"]},
    {"slug": "accuracy_btc_nf6", "args": ["--target-instrument", "btc", "--train-objective", "accuracy", "--n-folds", "6"]},
    {"slug": "margin_srcdir_expanded_nf6", "args": ["--target-instrument", "btc", "--train-objective", "margin_vs_bull", "--n-folds", "6", "--include-source-direction-signal", "--include-expanded-prior-features"]},
    {"slug": "accuracy_srcdir_expanded_nf6", "args": ["--target-instrument", "btc", "--train-objective", "accuracy", "--n-folds", "6", "--include-source-direction-signal", "--include-expanded-prior-features"]},
    {"slug": "margin_btc_nf5", "args": ["--target-instrument", "btc", "--train-objective", "margin_vs_bull", "--n-folds", "5"]},
    {"slug": "margin_kospi_nf6", "args": ["--target-instrument", "kospi", "--train-objective", "margin_vs_bull", "--n-folds", "6"]},
    {
        "slug": "margin_btc_regime_adaptive_nf6",
        "args": [
            "--target-instrument",
            "btc",
            "--train-objective",
            "margin_vs_bull",
            "--n-folds",
            "6",
            "--regime-adaptive-bull-train",
            "--regime-adaptive-lookback-days",
            "60",
        ],
    },
    {
        "slug": "margin_btc_regime_contrarian_guard_nf6",
        "args": [
            "--target-instrument",
            "btc",
            "--train-objective",
            "margin_vs_bull",
            "--n-folds",
            "6",
            "--regime-adaptive-bull-train",
            "--regime-adaptive-lookback-days",
            "60",
            "--regime-adaptive-contrarian-guard",
        ],
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--work-dir", type=Path, default=ROOT / "reports/_lens_wf_ablation_work")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.score_json.is_file():
        print(f"missing score: {args.score_json}", file=sys.stderr)
        return 2

    args.work_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for spec in VARIANTS:
        out = args.work_dir / f"lens_wf_{spec['slug']}.json"
        cmd = [
            sys.executable,
            str(WF),
            "--score-json",
            str(args.score_json),
            "--btc-csv",
            str(ROOT / "research/market_data/btc_daily_external_yf.csv"),
            "--kospi-csv",
            str(ROOT / "research/market_data/kospi_daily_external_yf.csv"),
            "--output",
            str(out),
            *spec["args"],
        ]
        rc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True).returncode
        row: dict[str, Any] = {"slug": spec["slug"], "exit_code": rc, "output_json": str(out.relative_to(ROOT)).replace("\\", "/")}
        if rc == 0 and out.is_file():
            doc = json.loads(out.read_text(encoding="utf-8-sig"))
            agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
            folds = doc.get("folds") if isinstance(doc.get("folds"), list) else []
            test_accs = [float(f.get("test_accuracy")) for f in folds if isinstance(f, dict) and isinstance(f.get("test_accuracy"), (int, float))]
            row.update(
                {
                    "mean_test_accuracy": agg.get("mean_test_accuracy"),
                    "stdev_test_accuracy": agg.get("stdev_test_accuracy"),
                    "min_test_accuracy": min(test_accs) if test_accs else None,
                    "beat_bull_frac": agg.get("fraction_test_beats_always_bull"),
                    "gate_055_pass": bool(isinstance(agg.get("mean_test_accuracy"), (int, float)) and float(agg["mean_test_accuracy"]) >= 0.55),
                }
            )
        else:
            row["error"] = "wf_failed"
        results.append(row)
        print(f"{spec['slug']}: mean={row.get('mean_test_accuracy')} pass055={row.get('gate_055_pass')}")

    best = max(
        (r for r in results if isinstance(r.get("mean_test_accuracy"), (int, float))),
        key=lambda x: float(x["mean_test_accuracy"]),
        default=None,
    )
    out_doc = {
        "schema": "lens_wf_regime_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "score_json": str(args.score_json.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
        "variants": results,
        "best_by_mean_test_accuracy": best,
        "any_gate_055_pass": any(r.get("gate_055_pass") for r in results),
        "note": "Lens WF on 180d nbps=2.0 score; not Track A promotion.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
