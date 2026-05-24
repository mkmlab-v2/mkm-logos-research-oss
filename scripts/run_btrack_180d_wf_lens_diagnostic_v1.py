#!/usr/bin/env python3
"""180d walk-forward recommended chain + wrong-direction lens report (reports/ only)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_180d_wf_lens_diagnostic_v1_latest.json"


def _run(cmd: list[str]) -> None:
    proc = subprocess.run([sys.executable, *cmd], cwd=ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"exit {proc.returncode}: {' '.join(cmd)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--neutral-bps", type=float, default=4.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    n = int(args.recent_trading_days)
    per_date_180 = ROOT / "reports" / f"btrack_ensemble_per_date_directions_{n}d_v1.json"
    score_180 = ROOT / "reports" / f"btrack_prophecy_score_recommended_{n}d_v1.json"
    lens_wf = ROOT / "reports" / f"prophecy_per_date_combo_walkforward_{n}d_v1.json"
    inst_wf = ROOT / "reports" / f"prophecy_instrument_combo_walkforward_{n}d_v1.json"
    gates = ROOT / "reports" / f"prophecy_promotion_gates_{n}d_v1.json"
    eval_180 = ROOT / "reports" / f"prophecy_hit_rate_eval_{n}d_v1.json"

    print(f"==> per-date directions {n}d", file=sys.stderr)
    _run(
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            str(n),
            "--output",
            f"reports/btrack_ensemble_per_date_directions_{n}d_v1.json",
        ]
    )
    print(f"==> recommended chain {n}d", file=sys.stderr)
    _run(
        [
            "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py",
            "--recent-trading-days",
            str(n),
            "--neutral-bps",
            str(args.neutral_bps),
            "--score-json",
            f"reports/btrack_prophecy_score_recommended_{n}d_v1.json",
            "--lens-walkforward-out",
            f"reports/prophecy_per_date_combo_walkforward_{n}d_v1.json",
            "--instrument-walkforward-out",
            f"reports/prophecy_instrument_combo_walkforward_{n}d_v1.json",
            "--gates-out",
            f"reports/prophecy_promotion_gates_{n}d_v1.json",
        ]
    )
    print("==> eval headline on 180d score panel", file=sys.stderr)
    _run(
        [
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            f"reports/btrack_prophecy_score_recommended_{n}d_v1.json",
            "--output",
            f"reports/prophecy_hit_rate_eval_{n}d_v1.json",
        ]
    )
    print("==> rebuild 30d per-date with lens_values for wrong-dir report", file=sys.stderr)
    _run(
        [
            "scripts/build_btrack_ensemble_per_date_directions_v1.py",
            "--recent-trading-days",
            "30",
        ]
    )
    _run(["scripts/build_btrack_headline_miss_report_v1.py"])
    _run(["scripts/build_btrack_wrong_direction_lens_report_v1.py"])

    lens_wf_doc = json.loads(lens_wf.read_text(encoding="utf-8"))
    eval_doc = json.loads(eval_180.read_text(encoding="utf-8"))
    wrong_lens = json.loads(
        (ROOT / "reports/btrack_wrong_direction_lens_report_v1_latest.json").read_text(encoding="utf-8")
    )
    agg = lens_wf_doc.get("aggregate") if isinstance(lens_wf_doc.get("aggregate"), dict) else {}
    report = {
        "schema": "btrack_180d_wf_lens_diagnostic_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "recent_trading_days": n,
        "neutral_bps": args.neutral_bps,
        "paths": {
            "per_date_json": str(per_date_180),
            "score_json": str(score_180),
            "lens_walkforward_json": str(lens_wf),
            "instrument_walkforward_json": str(inst_wf),
            "gates_json": str(gates),
            "eval_json": str(eval_180),
        },
        "walkforward_aggregate": {
            "mean_test_accuracy": agg.get("mean_test_accuracy"),
            "n_folds": agg.get("n_folds"),
        },
        "headline_eval_btc_panel": (eval_doc.get("metrics") or {}).get("legs", {}).get("btc")
        or eval_doc.get("metrics"),
        "wrong_direction_lens_summary": wrong_lens.get("summary"),
        "operator_lines": [
            f"- [MKM-180D-WF] lens WF mean_test_accuracy={agg.get('mean_test_accuracy')} (n_folds={agg.get('n_folds')})",
            (
                f"- [MKM-180D-WF] BTC panel all-rows "
                f"{(eval_doc.get('metrics') or {}).get('price_directional_hit_rate')}"
            ),
            wrong_lens.get("operator_line", ""),
        ],
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report.get("operator_lines") or []:
        if line:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
