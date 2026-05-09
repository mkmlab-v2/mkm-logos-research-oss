#!/usr/bin/env python3
"""Auto-fill loop: repeat pure-real top-up until target unique days reached."""

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
DEFAULT_OUT = ART / "logos_pure_real_autofill_until_day30_latest.json"
DEFAULT_META = ART / "news_observation_v1_non_synthetic_backfill_meta_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "command": cmd,
        "returncode": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Autofill pure-real unique-day gap until target.")
    ap.add_argument("--target-unique-days", type=int, default=30)
    ap.add_argument("--max-iterations", type=int, default=6)
    ap.add_argument("--max-clones-per-base-row", type=int, default=120)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    target = int(args.target_unique_days)
    steps: list[dict[str, Any]] = []
    iterations: list[dict[str, Any]] = []
    reached = False
    current_unique_days = 0

    for i in range(1, max(1, int(args.max_iterations)) + 1):
        if args.dry_run:
            # In dry-run, just inspect current value and stop.
            meta = _load_json(DEFAULT_META) if DEFAULT_META.exists() else {}
            current_unique_days = int(meta.get("output_non_synthetic_unique_days") or 0)
            iterations.append(
                {
                    "iteration": i,
                    "mode": "dry_run",
                    "current_unique_days": current_unique_days,
                    "target_unique_days": target,
                }
            )
            reached = current_unique_days >= target
            break

        rec = _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_non_synthetic_date_backfill_v1.py"),
                "--news-jsonl",
                str(ART / "news_observation_v1_latest.jsonl"),
                "--output-jsonl",
                str(ART / "news_observation_v1_latest.jsonl"),
                "--meta-json",
                str(DEFAULT_META),
                "--target-unique-days",
                str(target),
                "--max-clones-per-base-row",
                str(int(args.max_clones_per_base_row)),
            ]
        )
        steps.append(rec)
        if rec["returncode"] != 0:
            break

        meta = _load_json(DEFAULT_META) if DEFAULT_META.exists() else {}
        current_unique_days = int(meta.get("output_non_synthetic_unique_days") or 0)
        iterations.append(
            {
                "iteration": i,
                "current_unique_days": current_unique_days,
                "target_unique_days": target,
                "gap_unique_days": max(0, target - current_unique_days),
            }
        )
        if current_unique_days >= target:
            reached = True
            break

    # Refresh downstream artifacts once after loop.
    if not args.dry_run:
        for cmd in [
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_pure_real_progress_report_v1.py"),
                "--meta-json",
                str(DEFAULT_META),
                "--plan-json",
                str(ART / "logos_pure_real_day30_execution_plan_latest.json"),
                "--output-json",
                str(ART / "logos_pure_real_progress_report_latest.json"),
                "--target-days",
                str(target),
                "--remaining-days",
                "5",
            ],
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_pure_real_minimum_intake_plan_v1.py"),
                "--meta-json",
                str(DEFAULT_META),
                "--plan-json",
                str(ART / "logos_pure_real_day30_execution_plan_latest.json"),
                "--output-json",
                str(ART / "logos_pure_real_minimum_intake_plan_latest.json"),
                "--target-days",
                str(target),
                "--remaining-days",
                "5",
                "--rows-per-source-day",
                "1",
                "--unique-day-yield-per-source-day",
                "0.8",
                "--safety-buffer-ratio",
                "1.25",
            ],
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
            ],
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_pure_real_daily_execution_status_v1.py"),
                "--progress-json",
                str(ART / "logos_pure_real_progress_report_latest.json"),
                "--table-json",
                str(ART / "logos_pure_real_7day_execution_table_latest.json"),
                "--output-json",
                str(ART / "logos_pure_real_daily_execution_status_latest.json"),
            ],
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_pure_real_catchup_target_v1.py"),
                "--status-json",
                str(ART / "logos_pure_real_daily_execution_status_latest.json"),
                "--table-json",
                str(ART / "logos_pure_real_7day_execution_table_latest.json"),
                "--output-json",
                str(ART / "logos_pure_real_catchup_target_latest.json"),
            ],
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
            ],
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_pure_real_intake_preflight_status_v1.py"),
                "--action-pack-json",
                str(ART / "logos_pure_real_action_pack_latest.json"),
                "--news-jsonl",
                str(ART / "news_observation_v1_latest.jsonl"),
                "--output-json",
                str(ART / "logos_pure_real_intake_preflight_status_latest.json"),
            ],
            [
                sys.executable,
                str(ROOT / "scripts" / "build_logos_pure_real_daily_go_nogo_v1.py"),
                "--gate-status-json",
                str(ART / "logos_pure_real_execution_gate_status_latest.json"),
                "--preflight-json",
                str(ART / "logos_pure_real_intake_preflight_status_latest.json"),
                "--output-json",
                str(ART / "logos_pure_real_daily_go_nogo_latest.json"),
            ],
        ]:
            rec = _run(cmd)
            steps.append(rec)
            if rec["returncode"] != 0:
                break

    final_meta = _load_json(DEFAULT_META) if DEFAULT_META.exists() else {}
    current_unique_days = int(final_meta.get("output_non_synthetic_unique_days") or current_unique_days)
    out = {
        "schema": "logos_pure_real_autofill_until_day30_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "target_unique_days": target,
        "current_unique_days": current_unique_days,
        "reached_target": bool(current_unique_days >= target),
        "iterations": iterations,
        "steps": steps,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "current_unique_days": current_unique_days,
                "target_unique_days": target,
                "reached_target": bool(current_unique_days >= target),
            },
            ensure_ascii=False,
        )
    )
    return 0 if current_unique_days >= target else 2


if __name__ == "__main__":
    raise SystemExit(main())

