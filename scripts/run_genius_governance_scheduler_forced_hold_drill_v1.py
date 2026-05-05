#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.7, K:0.7, M:0.8}
# Balance: 88
# Purpose: Force two HOLD rows to validate auto-recovery and alert paths.
# Keywords: drill, hold, auto recovery, alert path
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    if cp.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{cp.stdout}\n{cp.stderr}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=ART / "genius_governance_scheduler_forced_hold_drill_latest.json")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    tmp = ART / "tmp_scheduler_forced_hold_drill"
    tmp.mkdir(parents=True, exist_ok=True)

    health_json = tmp / "health_hold.json"
    history_jsonl = tmp / "health_history_hold.jsonl"
    dispatch_history_jsonl = tmp / "health_history_dispatch_transition.jsonl"
    recovery_history_jsonl = tmp / "recovery_history_hold.jsonl"
    recovery_out = tmp / "recovery_out.json"
    dispatch_out = tmp / "dispatch_out.json"

    health_json.write_text(
        json.dumps(
            {
                "schema": "genius_governance_scheduler_health_check_v1",
                "generated_at_utc": _iso(now),
                "status": "HOLD",
                "summary": {"tasks_ok": False, "monthly_suite_pass": True, "unified_dashboard_go": True},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    hold_rows = [
        {"schema": "genius_governance_scheduler_health_history_row_v1", "ts_utc": _iso(now - timedelta(minutes=30)), "health_status": "HOLD"},
        {"schema": "genius_governance_scheduler_health_history_row_v1", "ts_utc": _iso(now), "health_status": "HOLD"},
    ]
    with history_jsonl.open("w", encoding="utf-8") as fh:
        for row in hold_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with dispatch_history_jsonl.open("w", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "schema": "genius_governance_scheduler_health_history_row_v1",
                    "ts_utc": _iso(now - timedelta(minutes=30)),
                    "health_status": "PASS",
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        fh.write(
            json.dumps(
                {
                    "schema": "genius_governance_scheduler_health_history_row_v1",
                    "ts_utc": _iso(now),
                    "health_status": "HOLD",
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    recovery_history_jsonl.write_text("", encoding="utf-8")

    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_genius_governance_scheduler_auto_recovery_v1.py"),
            "--health-history-jsonl",
            str(history_jsonl),
            "--recovery-history-jsonl",
            str(recovery_history_jsonl),
            "--hold-streak-threshold",
            "2",
            "--cooldown-minutes",
            "120",
            "--recovery-task-name",
            r"\MKM_GeniusHumanReview_HoldRehearsal_Monthly",
            "--output-json",
            str(recovery_out),
        ]
    )
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "dispatch_genius_governance_scheduler_health_alert_v1.py"),
            "--health-json",
            str(health_json),
            "--history-jsonl",
            str(dispatch_history_jsonl),
            "--min-hold-streak-to-dispatch",
            "1",
            "--output-json",
            str(dispatch_out),
        ]
    )

    rec = json.loads(recovery_out.read_text(encoding="utf-8"))
    dsp = json.loads(dispatch_out.read_text(encoding="utf-8"))
    out = {
        "schema": "genius_governance_scheduler_forced_hold_drill_v1",
        "generated_at_utc": _iso(datetime.now(timezone.utc)),
        "recovery_attempted": bool((rec.get("recovery") or {}).get("attempted")),
        "recovery_note": (rec.get("recovery") or {}).get("note"),
        "dispatch_should": bool((dsp.get("decision") or {}).get("should_dispatch")),
        "dispatch_status": (dsp.get("dispatch") or {}).get("status"),
        "pass": bool((rec.get("recovery") or {}).get("attempted")) and bool((dsp.get("decision") or {}).get("should_dispatch")),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "pass": out["pass"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
