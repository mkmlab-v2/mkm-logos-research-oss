#!/usr/bin/env python3
"""[HYPO] Parallel wave-5 — MS expansion rebuild + dual hybrid + anchor hybrids."""
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
OUT = ROOT / "reports/btrack_parallel_wave5_v1_latest.json"


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
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    tasks: list[tuple[str, list[str]]] = [
        (
            "ms_180d_expansion",
            [
                py,
                "-c",
                "from scripts.run_btrack_commander_approval_wave3_v1 import _ms_180d_expansion; "
                "import sys,json; print(json.dumps(_ms_180d_expansion(sys.executable), ensure_ascii=False))",
            ],
        ),
        (
            "hybrid_180d_anchor_ms",
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
            "v1_ms_hybrid_30d",
            [py, "scripts/run_btrack_v1_ms_hybrid_parallel_v1.py", "--max-workers", "5"],
        ),
        (
            "promotion_push_nbps2",
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
        ),
        ("parallel_wave2", [py, "scripts/run_btrack_parallel_wave2_v1.py", "--max-workers", "4"]),
        (
            "anchor_bundle",
            [
                py,
                "scripts/run_btrack_parallel_research_bundle_v1.py",
                "--include-anchor-promotion",
                "--max-workers",
                "6",
            ],
        ),
        (
            "ms_180d_matched",
            [
                py,
                "scripts/run_btrack_180d_active_day_matched_compare_v1.py",
                "--use-expansion-work",
            ],
        ),
        ("readiness", [py, "scripts/build_prophecy_promotion_readiness_report_v1.py"]),
    ]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futs = {pool.submit(_run, tid, cmd): tid for tid, cmd in tasks}
        for fut in as_completed(futs):
            results.append(fut.result())

    wk = _run("weekly_pack", [py, "scripts/run_btrack_weekly_prophecy_review_pack_v1.py"])
    results.append(wk)

    pack = {
        "schema": "btrack_parallel_wave5_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "live_trading_enabled": False,
        "parallel_tasks": sorted(results, key=lambda r: r["task_id"]),
        "all_ok": all(r.get("ok") for r in results),
        "artifacts": {
            "hybrid_anchor": "reports/btrack_hybrid_180d_promotion_parallel_v1_latest.json",
            "hybrid_expansion_ms": "reports/btrack_hybrid_180d_expansion_ms_promotion_parallel_v1_latest.json",
            "matched_180d": "reports/btrack_180d_active_day_matched_compare_v1_latest.json",
            "weekly": "reports/btrack_weekly_prophecy_review_pack_v1_latest.json",
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
