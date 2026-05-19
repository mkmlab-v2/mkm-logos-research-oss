#!/usr/bin/env python3
"""[HYPO] Wave-6 — daily-adjacent shadow ops + wrong-dir/min_conf + gates (no live)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/btrack_parallel_wave6_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
SCORE_BTC = ROOT / "docs/final/artifacts/btrack_prophecy_score_btc_only_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(task_id: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "task_id": task_id,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "").strip()[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--run-daily-chain", action="store_true", help="Also run PS1 daily chain (slow).")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    score_rel = "docs/final/artifacts/btrack_prophecy_score_latest.json"
    tasks: list[tuple[str, list[str]]] = [
        ("advisory_bear_trap", [py, "scripts/run_btrack_wrong_dir_holdout_v1.py", "advisory-sweep"]),
        ("model_swap_harness", [py, "scripts/run_btrack_model_swap_harness_v1.py"]),
        (
            "kpi_b_shadow",
            [py, "scripts/run_btrack_kpi_b_shadow_eval_v1.py", "--score-json", score_rel, "--btc-csv", str(BTC)],
        ),
        (
            "v1_per_date_30d",
            [
                py,
                "scripts/build_btrack_ensemble_per_date_directions_v1.py",
                "--recent-trading-days",
                "30",
                "--ensemble-mode",
                "v1",
                "--output",
                "reports/btrack_ensemble_per_date_directions_v1_latest.json",
            ],
        ),
        ("headline_miss", [py, "scripts/build_btrack_headline_miss_report_v1.py"]),
        ("wrong_dir_lens", [py, "scripts/build_btrack_wrong_direction_lens_report_v1.py"]),
        ("anchor_panel_snapshot", [py, "scripts/build_btrack_anchor_panel_hit_rate_snapshot_v1.py"]),
        ("p15_abstain_brief", [py, "scripts/build_btrack_p15_abstain_shadow_brief_v1.py"]),
        ("p15_daily_status", [py, "scripts/build_btrack_daily_p15_shadow_status_v1.py"]),
        (
            "min_conf_anchor",
            [py, "scripts/run_btrack_min_conf_experiment_v1.py", "--candidate-threshold", "0.35", "--btc-only"],
        ),
    ]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futs = {pool.submit(_run, tid, cmd): tid for tid, cmd in tasks}
        for fut in as_completed(futs):
            results.append(fut.result())

    if args.run_daily_chain:
        ps1 = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_btrack_daily_hypothesis_chain.ps1",
            "-SkipMarketDataRefresh",
            "-SkipLogosInsightBundle",
            "-SkipPhase3NetworkFetch",
        ]
        results.append(_run("daily_hypothesis_chain", ps1))

    results.append(_run("weekly_pack", [py, "scripts/run_btrack_weekly_prophecy_review_pack_v1.py"]))
    results.append(_run("eval_gates", [py, "scripts/eval_prophecy_promotion_gates_v1.py"]))
    results.append(_run("readiness", [py, "scripts/build_prophecy_promotion_readiness_report_v1.py"]))
    results.append(
        _run(
            "commander_finalize",
            [py, "scripts/run_btrack_commander_approval_finalize_v1.py", "--reviewer", "PRO"],
        )
    )

    pack = {
        "schema": "btrack_parallel_wave6_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "live_trading_enabled": False,
        "parallel_tasks": sorted(results, key=lambda r: r["task_id"]),
        "all_ok": all(r.get("ok") for r in results),
        "artifacts": {
            "weekly": "reports/btrack_weekly_prophecy_review_pack_v1_latest.json",
            "gates": "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json",
            "p15_daily": "reports/btrack_daily_p15_shadow_status_v1_latest.json",
            "wrong_dir_lens": "reports/btrack_wrong_direction_lens_report_v1_latest.json",
        },
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    failed = [r["task_id"] for r in results if not r.get("ok")]
    if failed:
        print(f"FAILED: {failed}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
