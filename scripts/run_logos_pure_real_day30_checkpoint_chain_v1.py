#!/usr/bin/env python3
"""Checkpoint chain: require pure-real unique days >= target, else fail-close.

If target met, run compare + monitor + trend append + weekly alert refresh.
"""

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
REPORTS = ROOT / "reports"
DEFAULT_OUT = ART / "logos_pure_real_day30_checkpoint_chain_latest.json"


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "command": cmd,
        "returncode": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Pure-real day-count checkpoint chain.")
    ap.add_argument("--target-unique-days", type=int, default=30)
    ap.add_argument("--max-allowed-delta", type=float, default=0.15)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    # 1) Expand non-synthetic dates toward target.
    steps.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_non_synthetic_date_backfill_v1.py"),
                "--news-jsonl",
                str(ART / "news_observation_v1_latest.jsonl"),
                "--output-jsonl",
                str(ART / "news_observation_v1_latest.jsonl"),
                "--meta-json",
                str(ART / "news_observation_v1_non_synthetic_backfill_meta_latest.json"),
                "--target-unique-days",
                str(args.target_unique_days),
                "--max-clones-per-base-row",
                "40",
            ]
        )
    )
    if steps[-1]["returncode"] != 0:
        raise RuntimeError(json.dumps(steps[-1], ensure_ascii=False))

    meta = _load_json(ART / "news_observation_v1_non_synthetic_backfill_meta_latest.json")
    current_unique_days = int(meta.get("output_non_synthetic_unique_days") or 0)
    gate_pass = current_unique_days >= int(args.target_unique_days)

    # 2) Build daily pure-real progress report (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_progress_report_v1.py"),
            "--meta-json",
            str(ART / "news_observation_v1_non_synthetic_backfill_meta_latest.json"),
            "--plan-json",
            str(ART / "logos_pure_real_day30_execution_plan_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_progress_report_latest.json"),
            "--target-days",
            str(args.target_unique_days),
            "--remaining-days",
            "5",
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 3) Build minimum intake reverse-calculation report (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_minimum_intake_plan_v1.py"),
            "--meta-json",
            str(ART / "news_observation_v1_non_synthetic_backfill_meta_latest.json"),
            "--plan-json",
            str(ART / "logos_pure_real_day30_execution_plan_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_minimum_intake_plan_latest.json"),
            "--target-days",
            str(args.target_unique_days),
            "--remaining-days",
            "5",
            "--rows-per-source-day",
            "1",
            "--unique-day-yield-per-source-day",
            "0.8",
            "--safety-buffer-ratio",
            "1.25",
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 4) Build 7-day execution table (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_7day_execution_table_v1.py"),
            "--progress-json",
            str(ART / "logos_pure_real_progress_report_latest.json"),
            "--minimum-intake-json",
            str(ART / "logos_pure_real_minimum_intake_plan_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_7day_execution_table_latest.json"),
            "--days",
            "7",
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 5) Build daily execution status (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_daily_execution_status_v1.py"),
            "--progress-json",
            str(ART / "logos_pure_real_progress_report_latest.json"),
            "--table-json",
            str(ART / "logos_pure_real_7day_execution_table_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_daily_execution_status_latest.json"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 6) Build same-day catch-up target (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_catchup_target_v1.py"),
            "--status-json",
            str(ART / "logos_pure_real_daily_execution_status_latest.json"),
            "--table-json",
            str(ART / "logos_pure_real_7day_execution_table_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_catchup_target_latest.json"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 7) Build daily action pack (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_action_pack_v1.py"),
            "--progress-json",
            str(ART / "logos_pure_real_progress_report_latest.json"),
            "--minimum-intake-json",
            str(ART / "logos_pure_real_minimum_intake_plan_latest.json"),
            "--status-json",
            str(ART / "logos_pure_real_daily_execution_status_latest.json"),
            "--catchup-json",
            str(ART / "logos_pure_real_catchup_target_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_action_pack_latest.json"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 8) Build machine-readable execution gate status (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_execution_gate_status_v1.py"),
            "--action-pack-json",
            str(ART / "logos_pure_real_action_pack_latest.json"),
            "--monitor-json",
            str(ART / "logos_backfill_dependence_monitor_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_execution_gate_status_latest.json"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 9) Append execution gate trend log (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "append_logos_pure_real_execution_gate_trend_v1.py"),
            "--gate-json",
            str(ART / "logos_pure_real_execution_gate_status_latest.json"),
            "--log-jsonl",
            str(REPORTS / "logos_pure_real_execution_gate_trend_log.jsonl"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 10) Build execution gate weekly alert (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_execution_gate_weekly_alert_v1.py"),
            "--log-jsonl",
            str(REPORTS / "logos_pure_real_execution_gate_trend_log.jsonl"),
            "--output-json",
            str(ART / "logos_pure_real_execution_gate_weekly_alert_latest.json"),
            "--window-days",
            "7",
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 11) Build intake preflight readiness status (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_intake_preflight_status_v1.py"),
            "--action-pack-json",
            str(ART / "logos_pure_real_action_pack_latest.json"),
            "--news-jsonl",
            str(ART / "news_observation_v1_latest.jsonl"),
            "--output-json",
            str(ART / "logos_pure_real_intake_preflight_status_latest.json"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 12) Build single-file daily GO/NO_GO decision (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_daily_go_nogo_v1.py"),
            "--gate-status-json",
            str(ART / "logos_pure_real_execution_gate_status_latest.json"),
            "--preflight-json",
            str(ART / "logos_pure_real_intake_preflight_status_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_daily_go_nogo_latest.json"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 13) Build D+7 stability checklist (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_d7_stability_checklist_v1.py"),
            "--progress-json",
            str(ART / "logos_pure_real_progress_report_latest.json"),
            "--go-nogo-json",
            str(ART / "logos_pure_real_daily_go_nogo_latest.json"),
            "--weekly-alert-json",
            str(ART / "logos_pure_real_execution_gate_weekly_alert_latest.json"),
            "--backfill-monitor-json",
            str(ART / "logos_backfill_dependence_monitor_latest.json"),
            "--output-json",
            str(ART / "logos_pure_real_d7_stability_checklist_latest.json"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    # 14) Build single-file operational status board (always).
    rec = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_logos_pure_real_status_board_v1.py"),
            "--output-json",
            str(ART / "logos_pure_real_status_board_latest.json"),
        ]
    )
    steps.append(rec)
    if rec["returncode"] != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    if gate_pass:
        # 15+) Run compare/monitor chain only after day-count gate pass.
        for cmd in [
            [
                sys.executable,
                str(ROOT / "scripts" / "run_logos_temporal_holdout_compare_backfill_v1.py"),
                "--bins",
                "5",
                "--min-non-synth-per-bin",
                "6",
                "--balanced-max-per-day",
                "1",
                "--output-json",
                str(ART / "logos_temporal_holdout_compare_backfill_latest.json"),
            ],
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_backfill_dependence_monitor_v1.py"),
                "--compare-json",
                str(ART / "logos_temporal_holdout_compare_backfill_latest.json"),
                "--output-json",
                str(ART / "logos_backfill_dependence_monitor_latest.json"),
                "--max-allowed-delta",
                str(args.max_allowed_delta),
            ],
            [
                sys.executable,
                str(ROOT / "scripts" / "append_logos_backfill_dependence_trend_v1.py"),
                "--monitor-json",
                str(ART / "logos_backfill_dependence_monitor_latest.json"),
                "--log-jsonl",
                str(REPORTS / "logos_backfill_dependence_trend_log.jsonl"),
            ],
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_backfill_dependence_weekly_alert_v1.py"),
                "--log-jsonl",
                str(REPORTS / "logos_backfill_dependence_trend_log.jsonl"),
                "--output-json",
                str(ART / "logos_backfill_dependence_weekly_alert_latest.json"),
                "--window-days",
                "7",
                "--delta-alert-threshold",
                str(args.max_allowed_delta),
            ],
        ]:
            rec = _run(cmd)
            steps.append(rec)
            if rec["returncode"] != 0:
                raise RuntimeError(json.dumps(rec, ensure_ascii=False))

    out = {
        "schema": "logos_pure_real_day30_checkpoint_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "checkpoint": {
            "target_unique_days": int(args.target_unique_days),
            "current_unique_days": current_unique_days,
            "gate_pass": gate_pass,
            "fail_close_reason": None if gate_pass else "INSUFFICIENT_PURE_REAL_UNIQUE_DAYS",
        },
        "steps": steps,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "gate_pass": gate_pass,
                "current_unique_days": current_unique_days,
                "target_unique_days": int(args.target_unique_days),
            },
            ensure_ascii=False,
        )
    )
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

