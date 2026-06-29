#!/usr/bin/env python3
"""[HYPO] AB: lens WF grid constraints (min w_cross / regime-adaptive) vs baseline."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "scripts/run_prophecy_per_date_combo_walkforward_v1.py"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btc_lens_wf_grid_constraint_ablation_v1_latest.json"
WORK = ROOT / "reports/_btc_lens_wf_grid_constraint_work"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"

VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline", "args": []},
    {"slug": "min_w_cross_0", "args": ["--train-min-w-cross", "0"]},
    {"slug": "min_w_self_0_cross_0", "args": ["--train-min-w-self", "0", "--train-min-w-cross", "0"]},
    {
        "slug": "regime_adaptive_min_w_cross",
        "args": [
            "--regime-adaptive-min-w-cross",
            "--regime-bull-train-floor",
            "0.45",
            "--regime-adaptive-lookback-days",
            "60",
        ],
    },
    {
        "slug": "regime_min_cross_plus_contrarian_guard",
        "args": [
            "--regime-adaptive-min-w-cross",
            "--regime-bull-train-floor",
            "0.45",
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
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    if not score.is_file():
        raise SystemExit(f"missing score: {score}")

    WORK.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict[str, Any]] = []
    for spec in VARIANTS:
        out = WORK / f"lens_wf_{spec['slug']}.json"
        cmd = [
            sys.executable,
            str(WF),
            "--score-json",
            str(score),
            "--btc-csv",
            str(BTC),
            "--target-instrument",
            "btc",
            "--train-objective",
            "margin_vs_bull",
            "--n-folds",
            "6",
            "--output",
            str(out),
            *spec["args"],
        ]
        rc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True).returncode
        row: dict[str, Any] = {"slug": spec["slug"], "exit_code": rc, "args": spec["args"]}
        if rc == 0 and out.is_file():
            doc = json.loads(out.read_text(encoding="utf-8-sig"))
            agg = doc.get("aggregate") if isinstance(doc.get("aggregate"), dict) else {}
            row["mean_test_accuracy"] = agg.get("mean_test_accuracy")
            row["beat_bull_frac"] = agg.get("fraction_test_beats_always_bull")
            row["gate_055_pass"] = bool(
                isinstance(agg.get("mean_test_accuracy"), (int, float)) and float(agg["mean_test_accuracy"]) >= 0.55
            )
            folds = doc.get("folds") if isinstance(doc.get("folds"), list) else []
            f3 = next((f for f in folds if isinstance(f, dict) and f.get("fold_index") == 3), None)
            if isinstance(f3, dict):
                row["fold3_test_accuracy"] = (f3.get("test") or {}).get("accuracy")
                row["fold3_w_cross"] = (f3.get("best_params_from_train") or {}).get("w_cross")
        rows_out.append(row)
        print(f"{spec['slug']}: mean={row.get('mean_test_accuracy')} f3={row.get('fold3_test_accuracy')}")

    best = max(
        (r for r in rows_out if isinstance(r.get("mean_test_accuracy"), (int, float))),
        key=lambda x: float(x["mean_test_accuracy"]),
        default=None,
    )
    baseline = next((r for r in rows_out if r.get("slug") == "baseline"), {})
    doc = {
        "schema": "btc_lens_wf_grid_constraint_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "score_json": str(score.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
        "variants": rows_out,
        "best_by_mean_test_accuracy": best,
        "delta_best_minus_baseline_mean": (
            round(float(best["mean_test_accuracy"]) - float(baseline["mean_test_accuracy"]), 6)
            if best and isinstance(baseline.get("mean_test_accuracy"), (int, float)) and isinstance(best.get("mean_test_accuracy"), (int, float))
            else None
        ),
        "any_gate_055_pass": any(r.get("gate_055_pass") for r in rows_out),
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
