#!/usr/bin/env python3
"""[HYPO] B-track autopilot — post-approval parallel refresh (no live/auto_bridge)."""
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
OUT = ROOT / "reports/btrack_autopilot_v1_latest.json"
WORK = ROOT / "reports/btrack_ms_180d_expansion_work"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(task_id: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "task_id": task_id,
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "").strip()[-600:],
    }


def _governance_snapshot() -> dict[str, Any]:
    snap: dict[str, Any] = {}
    for rel in (
        "docs/final/artifacts/prophecy_manual_promotion_decision_lock_v1_latest.json",
        "docs/final/artifacts/prophecy_release_signoff_packet_v1_latest.json",
        "docs/final/artifacts/prophecy_approved_candidate_release_checklist_v1_latest.json",
        "docs/final/artifacts/prophecy_track_a_candidate_v1_latest.json",
    ):
        p = ROOT / rel
        if p.is_file():
            o = json.loads(p.read_text(encoding="utf-8"))
            snap[rel] = {
                "final_decision": o.get("final_decision"),
                "status": o.get("status"),
                "ready": (o.get("summary") or {}).get("ready_for_release_signoff")
                if "summary" in o
                else o.get("ready_for_release_signoff"),
            }
    return snap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--include-heavy-bundle", action="store_true")
    ap.add_argument("--refresh-commander-lock", action="store_true", help="Re-run finalize (default: skip).")
    ap.add_argument(
        "--include-promotion-push",
        action="store_true",
        help="Run run_btrack_promotion_push_v1 (180d v1 sweep; may overwrite strict dual SSOT — default skip).",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    results: list[dict[str, Any]] = []

    if args.refresh_commander_lock:
        results.append(
            _run(
                "commander_finalize",
                [py, "scripts/run_btrack_commander_approval_finalize_v1.py", "--reviewer", "PRO"],
            )
        )

    parallel: list[tuple[str, list[str]]] = [
        (
            "hybrid_180d_nbps2",
            [py, "scripts/run_btrack_hybrid_180d_promotion_parallel_v1.py", "--neutral-bps", "2.0"],
        ),
        (
            "parallel_wave2",
            [py, "scripts/run_btrack_parallel_wave2_v1.py", "--max-workers", "4"],
        ),
    ]
    bundle_cmd = [
        py,
        "scripts/run_btrack_parallel_research_bundle_v1.py",
        "--include-anchor-promotion",
        "--max-workers",
        "6",
    ]
    if not args.include_heavy_bundle:
        bundle_cmd.append("--skip-heavy")
    parallel.append(("parallel_bundle", bundle_cmd))
    if args.include_promotion_push:
        parallel.insert(
            0,
            (
                "promotion_push",
                [py, "scripts/run_btrack_promotion_push_v1.py"],
            ),
        )

    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futs = {pool.submit(_run, tid, cmd): tid for tid, cmd in parallel}
        for fut in as_completed(futs):
            results.append(fut.result())

    results.append(_run("weekly_pack", [py, "scripts/run_btrack_weekly_prophecy_review_pack_v1.py"]))

    # MS-180d matched refresh (v1 per-date + expanded sidecar) without full wave3 finalize
    results.append(
        _run(
            "ms_180d_matched",
            [
                py,
                "scripts/run_btrack_180d_active_day_matched_compare_v1.py",
                "--use-expansion-work",
            ],
        )
    )
    if WORK.is_dir():
        results.append(
            _run(
                "ms_180d_expansion_rebuild",
                [
                    py,
                    "-c",
                    "from scripts.run_btrack_commander_approval_wave3_v1 import _ms_180d_expansion; "
                    "import sys, json; r=_ms_180d_expansion(sys.executable); "
                    "print(json.dumps({'ok':r.get('ok'),'lanes':r.get('matched_lanes')}))",
                ],
            )
        )

    results.append(
        _run(
            "readiness_push",
            [py, "scripts/build_prophecy_promotion_readiness_report_v1.py"],
        )
    )

    pack = {
        "schema": "btrack_autopilot_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "live_trading_enabled": False,
        "tasks": results,
        "all_ok": all(r.get("ok") for r in results),
        "governance": _governance_snapshot(),
        "operator_lines": [
            "- [MKM-AUTO] Post-approval autopilot; live/auto_bridge OFF.",
            "- [MKM-AUTO] 30d frozen headline unchanged; 180d soft_band research lane.",
            "- [MKM-AUTO] See reports/btrack_weekly_prophecy_review_pack_v1_latest.json",
        ],
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    failed = [r["task_id"] for r in results if not r.get("ok")]
    if failed:
        print(f"FAILED: {failed}", file=sys.stderr)
    gov = pack.get("governance") or {}
    lock = gov.get("docs/final/artifacts/prophecy_manual_promotion_decision_lock_v1_latest.json") or {}
    print(f"lock={lock.get('final_decision')} packet={gov.get('docs/final/artifacts/prophecy_release_signoff_packet_v1_latest.json', {}).get('status')}")
    return 0 if pack["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
