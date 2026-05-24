#!/usr/bin/env python3
"""[HYPO] Parallel wave-2 B-track research lanes (180d diagnostics + experiments)."""
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
OUT = ROOT / "reports/btrack_parallel_wave2_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_task(task_id: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or cp.stderr or "").strip()[-600:]
    return {
        "task_id": task_id,
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": tail,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    tasks: list[tuple[str, list[str]]] = [
        (
            "matched_180d",
            [py, "scripts/run_btrack_180d_active_day_matched_compare_v1.py"],
        ),
        (
            "wf_lens_diagnostic_180d",
            [
                py,
                "scripts/run_btrack_180d_wf_lens_diagnostic_v1.py",
                "--recent-trading-days",
                "180",
                "--neutral-bps",
                "2.0",
            ],
        ),
        (
            "wrong_dir_sign_inversion_30d",
            [py, "scripts/run_btrack_wrong_dir_sign_inversion_experiment_v1.py"],
        ),
        (
            "min_conf_grid_anchor",
            [
                py,
                "scripts/run_btrack_min_conf_experiment_v1.py",
                "--grid",
                "0.12,0.15,0.18,0.22,0.25,0.30",
                "--btc-only",
            ],
        ),
        (
            "holdout_oos_180d",
            [py, "scripts/build_btrack_holdout_gate_oos_180d_eval_v1.py"],
        ),
    ]

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futures = {pool.submit(_run_task, tid, cmd): tid for tid, cmd in tasks}
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda r: str(r.get("task_id") or ""))

    pack = {
        "schema": "btrack_parallel_wave2_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "parallel_tasks": results,
        "artifacts": {
            "matched_180d": "reports/btrack_180d_active_day_matched_compare_v1_latest.json",
            "wf_lens_diagnostic": "reports/btrack_180d_wf_lens_diagnostic_v1_latest.json",
            "wrong_dir_sign_inversion": "reports/btrack_wrong_dir_sign_inversion_experiment_v1_latest.json",
            "min_conf_grid": "reports/btrack_min_conf_experiment_grid_v1_latest.json",
            "holdout_oos_180d": "reports/btrack_holdout_gate_oos_180d_v1_latest.json",
        },
        "all_ok": all(r.get("ok") for r in results),
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
