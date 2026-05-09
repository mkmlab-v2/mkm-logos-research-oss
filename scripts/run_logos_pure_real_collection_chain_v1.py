#!/usr/bin/env python3
"""Run pure-real collection chain and backfill dependence monitoring."""

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
DEFAULT_OUT = ART / "logos_pure_real_collection_chain_latest.json"


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    rec: dict[str, Any] = {
        "command": cmd,
        "returncode": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }
    if cp.returncode != 0:
        raise RuntimeError(json.dumps(rec, ensure_ascii=False))
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="Run pure-real collection + compare + monitor chain.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-allowed-delta", type=float, default=0.15)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    # 1) External ingest append (pure-real source expansion).
    steps.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_news_observation_from_external_feed_v1.py"),
                "--external-feed-json",
                str(ART / "external_feed_drop_latest.validated.json"),
                "--external-news-json",
                str(ART / "external_news_feed_latest.json"),
                "--external-macro-json",
                str(ART / "external_macro_signals_latest.json"),
                "--btc-alt-json",
                str(ART / "btc_alt_public_signals_latest.json"),
                "--output-jsonl",
                str(ART / "news_observation_v1_latest.jsonl"),
                "--append-existing-jsonl",
                str(ART / "news_observation_v1_latest.jsonl"),
                "--enable-asof-clamp",
                "--validate",
            ]
        )
    )

    # 2) Restore/maintain day30 unique-day target after ingest.
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
                "30",
                "--max-clones-per-base-row",
                "200",
            ]
        )
    )

    # 3) Re-run pure-vs-mixed compare.
    steps.append(
        _run(
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
            ]
        )
    )

    # 4) Build monitor report.
    steps.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_backfill_dependence_monitor_v1.py"),
                "--compare-json",
                str(ART / "logos_temporal_holdout_compare_backfill_latest.json"),
                "--output-json",
                str(ART / "logos_backfill_dependence_monitor_latest.json"),
                "--max-allowed-delta",
                str(args.max_allowed_delta),
            ]
        )
    )

    # 5) Append trend record.
    steps.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "append_logos_backfill_dependence_trend_v1.py"),
                "--monitor-json",
                str(ART / "logos_backfill_dependence_monitor_latest.json"),
                "--log-jsonl",
                str(ROOT / "reports" / "logos_backfill_dependence_trend_log.jsonl"),
            ]
        )
    )

    # 6) Build weekly alert summary.
    steps.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_backfill_dependence_weekly_alert_v1.py"),
                "--log-jsonl",
                str(ROOT / "reports" / "logos_backfill_dependence_trend_log.jsonl"),
                "--output-json",
                str(ART / "logos_backfill_dependence_weekly_alert_latest.json"),
                "--window-days",
                "7",
                "--delta-alert-threshold",
                str(args.max_allowed_delta),
            ]
        )
    )

    # 7) Build daily pure-real progress report.
    steps.append(
        _run(
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
                "30",
                "--remaining-days",
                "5",
            ]
        )
    )

    # 8) Build minimum intake reverse-calculation report.
    steps.append(
        _run(
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
                "30",
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
    )

    # 9) Build 7-day execution table (today~D+6).
    steps.append(
        _run(
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
    )

    # 10) Build daily execution status (on-track/off-track).
    steps.append(
        _run(
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
    )

    # 11) Build same-day catch-up target.
    steps.append(
        _run(
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
    )

    # 12) Build daily action pack.
    steps.append(
        _run(
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
    )

    # 13) Build machine-readable execution gate status.
    steps.append(
        _run(
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
    )

    # 14) Append execution gate trend log.
    steps.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "append_logos_pure_real_execution_gate_trend_v1.py"),
                "--gate-json",
                str(ART / "logos_pure_real_execution_gate_status_latest.json"),
                "--log-jsonl",
                str(ROOT / "reports" / "logos_pure_real_execution_gate_trend_log.jsonl"),
            ]
        )
    )

    # 15) Build execution gate weekly alert.
    steps.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_pure_real_execution_gate_weekly_alert_v1.py"),
                "--log-jsonl",
                str(ROOT / "reports" / "logos_pure_real_execution_gate_trend_log.jsonl"),
                "--output-json",
                str(ART / "logos_pure_real_execution_gate_weekly_alert_latest.json"),
                "--window-days",
                "7",
            ]
        )
    )

    # 16) Build intake preflight readiness status.
    steps.append(
        _run(
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
    )

    # 17) Build single-file daily GO/NO_GO decision.
    steps.append(
        _run(
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
    )

    # 18) Build D+7 stability checklist.
    steps.append(
        _run(
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
    )

    # 19) Build single-file operational status board.
    steps.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_pure_real_status_board_v1.py"),
                "--output-json",
                str(ART / "logos_pure_real_status_board_latest.json"),
            ]
        )
    )

    out = {
        "schema": "logos_pure_real_collection_chain_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "steps": steps,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "step_count": len(steps)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

