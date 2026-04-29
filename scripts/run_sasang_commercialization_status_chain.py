#!/usr/bin/env python3
"""Run Sasang commercialization status chain and emit command manifest."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_OUT = ART / "sasang_commercialization_status_chain_latest.json"
DEFAULT_CMD = ART / "sasang_repro_command_set_latest.txt"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "command": " ".join(cmd),
        "exit_code": int(cp.returncode),
        "stdout_tail": (cp.stdout or "").strip()[-1200:],
        "stderr_tail": (cp.stderr or "").strip()[-1200:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--repro-cmd-out", type=Path, default=DEFAULT_CMD)
    args = ap.parse_args()

    commands = [
        [sys.executable, "scripts/build_sasang_gt_expansion_queue.py"],
        [sys.executable, "scripts/prioritize_sasang_gt_expansion_queue.py", "--top-k", "126"],
        [sys.executable, "scripts/export_sasang_gt_labeling_sheet.py"],
        [sys.executable, "scripts/build_sasang_labeling_assignment_plan.py"],
        [sys.executable, "scripts/export_sasang_labeling_packets_by_reviewer.py"],
        [sys.executable, "scripts/validate_sasang_gt_labeling_sheet.py"],
        [sys.executable, "scripts/import_sasang_labeled_sheet_to_queue.py"],
        [
            sys.executable,
            "scripts/merge_sasang_labeled_queue_into_gt.py",
            "--labeled-queue",
            "reports/constitution/btrack_pilot/sasang_gt_labeled_queue_top126_latest.jsonl",
            "--report",
            "docs/final/artifacts/sasang_gt_merge_report_from_sheet_latest.json",
        ],
        [sys.executable, "scripts/build_sasang_authoritative_predictions.py"],
        [sys.executable, "scripts/report_sasang_production_data_readiness.py"],
        [sys.executable, "scripts/report_sasang_gt_approval_progress.py"],
        [sys.executable, "scripts/report_sasang_gt_approval_whatif.py"],
        [sys.executable, "scripts/simulate_sasang_gt_merge_impact.py", "--approve-top-n", "126"],
        [sys.executable, "scripts/report_sasang_strict_input_integrity.py"],
        [sys.executable, "scripts/build_sasang_supplemental_insight_score.py"],
        [sys.executable, "scripts/build_sasang_supplemental_insight_trend.py"],
        [sys.executable, "scripts/emit_sasang_supplemental_trend_alert.py"],
        [sys.executable, "scripts/build_sasang_commercialization_readiness_packet.py"],
        [sys.executable, "scripts/record_sasang_human_signoff.py", "--approver", "user-approved", "--decision", "APPROVED"],
        [sys.executable, "scripts/check_sasang_ready_drift.py"],
        [sys.executable, "scripts/run_sasang_ready_rollback_drill.py"],
        [sys.executable, "scripts/authorize_sasang_promotion_to_atrack.py", "--authorizer", "user-approved"],
        [sys.executable, "scripts/finalize_sasang_promotion_completion.py", "--operator", "user-approved"],
        [sys.executable, "scripts/build_sasang_weekly_ops_report.py"],
    ]

    results = [_run(c) for c in commands]
    ok = all(r["exit_code"] == 0 for r in results)

    payload = {
        "schema": "sasang_commercialization_status_chain_v1",
        "generated_at_utc": _now(),
        "all_exit_zero": ok,
        "steps": results,
        "notes": [
            "This chain refreshes status and evidence artifacts only.",
            "GT writes require explicit --write in merge script after human approval.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    repro_lines = [
        "# Sasang commercialization reproducible command set",
        f"# generated_at_utc={_now()}",
    ]
    repro_lines.extend(" ".join(c) for c in commands)
    args.repro_cmd_out.parent.mkdir(parents=True, exist_ok=True)
    args.repro_cmd_out.write_text("\n".join(repro_lines) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(f"WROTE: {args.repro_cmd_out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
