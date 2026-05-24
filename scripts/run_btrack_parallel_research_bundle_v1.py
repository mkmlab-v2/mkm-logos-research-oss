#!/usr/bin/env python3
"""[HYPO] Parallel B-track research bundle — anchor panel lanes in one shot."""
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
OUT = ROOT / "reports/btrack_parallel_research_bundle_v1_latest.json"

ANCHOR_SCORE = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
KPI_B_SCORE_OUT = ROOT / "reports/btrack_prophecy_score_kpi_b_anchor_30d_v1.json"
KPI_B_EVAL_OUT = ROOT / "reports/prophecy_hit_rate_eval_kpi_b_anchor_30d_v1.json"
KPI_B_SUMMARY = ROOT / "reports/btrack_kpi_b_shadow_anchor_30d_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def _run_task(task_id: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or cp.stderr or "").strip()[-500:]
    return {
        "task_id": task_id,
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": tail,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument(
        "--skip-heavy",
        action="store_true",
        help="Skip aligned_30d and hybrid_parallel (faster refresh).",
    )
    ap.add_argument(
        "--include-anchor-promotion",
        action="store_true",
        help="Run run_btrack_anchor_panel_promotion_parallel_v1.py (WF+gates per lane).",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    tasks: list[tuple[str, list[str]]] = []

    if not args.skip_heavy:
        tasks.append(("aligned_30d", [py, "scripts/run_btrack_aligned_30d_experiment_v1.py"]))
        tasks.append(
            (
                "hybrid_parallel",
                [py, "scripts/run_btrack_v1_ms_hybrid_parallel_v1.py", "--max-workers", "5"],
            )
        )

    tasks.extend(
        [
            ("matched_compare", [py, "scripts/run_btrack_active_day_matched_compare_v1.py"]),
            (
                "parallel_lens_coverage",
                [py, "scripts/run_btrack_parallel_lens_coverage_v1.py"],
            ),
            (
                "kpi_b_anchor_shadow",
                [
                    py,
                    "scripts/run_btrack_kpi_b_shadow_eval_v1.py",
                    "--score-json",
                    _rel(ANCHOR_SCORE),
                    "--score-out",
                    _rel(KPI_B_SCORE_OUT),
                    "--eval-out",
                    _rel(KPI_B_EVAL_OUT),
                    "--summary-out",
                    _rel(KPI_B_SUMMARY),
                    "--kpi-a-eval-json",
                    "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json",
                ],
            ),
            (
                "hit_rate_snapshot",
                [py, "scripts/build_btrack_anchor_panel_hit_rate_snapshot_v1.py"],
            ),
        ]
    )
    if args.include_anchor_promotion:
        tasks.append(
            (
                "anchor_promotion_gates",
                [py, "scripts/run_btrack_anchor_panel_promotion_parallel_v1.py", "--max-workers", "3"],
            )
        )

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futures = {
            pool.submit(_run_task, tid, cmd): tid for tid, cmd in tasks
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: str(r.get("task_id") or ""))

    weekly: dict[str, Any] = {}
    wk = _run_task(
        "weekly_pack",
        [py, "scripts/run_btrack_weekly_prophecy_review_pack_v1.py"],
    )
    weekly = wk

    pack = {
        "schema": "btrack_parallel_research_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "parallel_tasks": results,
        "weekly_pack": weekly,
        "artifacts": {
            "bundle_summary": _rel(OUT),
            "weekly_pack": "reports/btrack_weekly_prophecy_review_pack_v1_latest.json",
            "hit_rate_snapshot": "reports/btrack_anchor_panel_hit_rate_snapshot_v1_latest.json",
            "hybrid_parallel": "reports/btrack_v1_ms_hybrid_parallel_v1_latest.json",
            "matched_compare": "reports/btrack_active_day_matched_compare_v1_latest.json",
            "kpi_b_anchor_summary": _rel(KPI_B_SUMMARY),
            "anchor_promotion_parallel": "reports/btrack_anchor_panel_promotion_parallel_v1_latest.json",
        },
        "all_parallel_ok": all(r.get("ok") for r in results),
        "weekly_ok": weekly.get("ok"),
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    failed = [r["task_id"] for r in results if not r.get("ok")]
    if failed:
        print(f"FAILED parallel: {failed}", file=sys.stderr)
    if not weekly.get("ok"):
        print("FAILED weekly_pack", file=sys.stderr)
    return 0 if pack["all_parallel_ok"] and pack["weekly_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
