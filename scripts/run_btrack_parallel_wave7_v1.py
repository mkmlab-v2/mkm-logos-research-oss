#!/usr/bin/env python3
"""[HYPO] Wave-7 — max parallel B-track research (no prod apply / no live)."""
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
OUT = ROOT / "reports/btrack_parallel_wave7_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"


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
    ap.add_argument("--max-workers", type=int, default=8)
    ap.add_argument(
        "--include-promotion-push",
        action="store_true",
        help="Serial nbps sweep after parallel (mutates recommended chain; not prod apply).",
    )
    ap.add_argument(
        "--skip-serial-tail",
        action="store_true",
        help="Skip weekly/readiness/gates/commander_finalize (shadow-only refresh).",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    parallel: list[tuple[str, list[str]]] = [
        ("hybrid_30d", [py, "scripts/run_btrack_v1_ms_hybrid_parallel_v1.py", "--max-workers", "5"]),
        (
            "hybrid_180d_anchor",
            [py, "scripts/run_btrack_hybrid_180d_promotion_parallel_v1.py", "--neutral-bps", "2.0"],
        ),
        (
            "hybrid_180d_expansion_ms",
            [
                py,
                "scripts/run_btrack_hybrid_180d_promotion_parallel_v1.py",
                "--neutral-bps",
                "2.0",
                "--use-expansion-ms",
            ],
        ),
        (
            "parallel_bundle",
            [
                py,
                "scripts/run_btrack_parallel_research_bundle_v1.py",
                "--include-anchor-promotion",
                "--max-workers",
                "6",
            ],
        ),
        ("parallel_wave2", [py, "scripts/run_btrack_parallel_wave2_v1.py", "--max-workers", "4"]),
        ("aligned_30d", [py, "scripts/run_btrack_aligned_30d_experiment_v1.py"]),
        ("parallel_lens_coverage", [py, "scripts/run_btrack_parallel_lens_coverage_v1.py"]),
        ("active_day_matched_30d", [py, "scripts/run_btrack_active_day_matched_compare_v1.py"]),
        (
            "ms_180d_matched",
            [
                py,
                "scripts/run_btrack_180d_active_day_matched_compare_v1.py",
                "--use-expansion-work",
            ],
        ),
        (
            "ms_180d_expansion",
            [
                py,
                "-c",
                "from scripts.run_btrack_commander_approval_wave3_v1 import _ms_180d_expansion; "
                "import sys,json; print(json.dumps(_ms_180d_expansion(sys.executable), ensure_ascii=False)[:800])",
            ],
        ),
        ("wf_lens_180d", [py, "scripts/run_btrack_180d_wf_lens_diagnostic_v1.py"]),
        ("advisory_sweep", [py, "scripts/run_btrack_wrong_dir_holdout_v1.py", "advisory-sweep"]),
        ("model_swap", [py, "scripts/run_btrack_model_swap_harness_v1.py"]),
        ("wrong_dir_sign_inv", [py, "scripts/run_btrack_wrong_dir_sign_inversion_experiment_v1.py"]),
        (
            "kpi_b_shadow",
            [
                py,
                "scripts/run_btrack_kpi_b_shadow_eval_v1.py",
                "--score-json",
                "docs/final/artifacts/btrack_prophecy_score_latest.json",
                "--btc-csv",
                str(BTC),
            ],
        ),
        (
            "min_conf_grid",
            [
                py,
                "scripts/run_btrack_min_conf_experiment_v1.py",
                "--grid",
                "0.18,0.20,0.22,0.25,0.30,0.35",
                "--btc-only",
            ],
        ),
        ("headline_miss", [py, "scripts/build_btrack_headline_miss_report_v1.py"]),
        ("wrong_dir_lens", [py, "scripts/build_btrack_wrong_direction_lens_report_v1.py"]),
        ("anchor_snapshot", [py, "scripts/build_btrack_anchor_panel_hit_rate_snapshot_v1.py"]),
        ("p15_brief", [py, "scripts/build_btrack_p15_abstain_shadow_brief_v1.py"]),
    ]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futs = {pool.submit(_run, tid, cmd): tid for tid, cmd in parallel}
        for fut in as_completed(futs):
            results.append(fut.result())

    if args.include_promotion_push:
        results.append(
            _run(
                "promotion_push_sweep",
                [
                    py,
                    "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py",
                    "--recent-trading-days",
                    "180",
                    "--neutral-bps",
                    "2.0",
                    "--auto-sweep-and-apply",
                    "--auto-sweep-grid",
                    "2,2.5,3,4",
                ],
            )
        )

    if not args.skip_serial_tail:
        serial_tail = [
            ("weekly_pack", [py, "scripts/run_btrack_weekly_prophecy_review_pack_v1.py"]),
            ("readiness", [py, "scripts/build_prophecy_promotion_readiness_report_v1.py"]),
            ("eval_gates", [py, "scripts/eval_prophecy_promotion_gates_v1.py"]),
            (
                "commander_finalize",
                [py, "scripts/run_btrack_commander_approval_finalize_v1.py", "--reviewer", "PRO"],
            ),
        ]
        for tid, cmd in serial_tail:
            results.append(_run(tid, cmd))

    pack = {
        "schema": "btrack_parallel_wave7_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "live_trading_enabled": False,
        "max_workers": args.max_workers,
        "parallel_tasks": sorted(results, key=lambda r: r["task_id"]),
        "all_ok": all(r.get("ok") for r in results),
        "failed": [r["task_id"] for r in results if not r.get("ok")],
        "artifacts": {
            "bundle": "reports/btrack_parallel_research_bundle_v1_latest.json",
            "wave2": "reports/btrack_parallel_wave2_v1_latest.json",
            "hybrid_30d": "reports/btrack_v1_ms_hybrid_parallel_v1_latest.json",
            "hybrid_180d": "reports/btrack_hybrid_180d_promotion_parallel_v1_latest.json",
            "weekly": "reports/btrack_weekly_prophecy_review_pack_v1_latest.json",
            "min_conf_grid": "reports/btrack_min_conf_experiment_grid_v1_latest.json",
        },
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if pack["failed"]:
        print(f"FAILED: {pack['failed']}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
