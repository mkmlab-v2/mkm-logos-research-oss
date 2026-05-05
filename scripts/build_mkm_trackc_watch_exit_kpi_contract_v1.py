#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Track C WATCH-exit KPI contract artifact.")
    ap.add_argument("--min-weekly-pass-rate", type=float, default=95.0)
    ap.add_argument("--min-weekly-sample-count", type=int, default=3)
    ap.add_argument("--max-watch-days", type=int, default=14)
    ap.add_argument("--min-guard-pass-ratio", type=float, default=1.0)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/mkm_trackc_watch_exit_kpi_contract_latest.json",
    )
    args = ap.parse_args()

    out_path = resolve(args.output_json)
    payload = {
        "schema": "mkm_trackc_watch_exit_kpi_contract_v1",
        "generated_at_utc": utc_now(),
        "contract_version": "v1",
        "goal": "define numeric exit criteria for WATCH to controlled expansion",
        "watch_exit_kpis": {
            "min_weekly_pass_rate_percent": args.min_weekly_pass_rate,
            "min_weekly_sample_count": args.min_weekly_sample_count,
            "max_watch_days_without_recheck": args.max_watch_days,
            "min_guard_pass_ratio": args.min_guard_pass_ratio,
        },
        "decision_mapping": {
            "all_kpis_pass": "GO_EXPAND_CANDIDATE",
            "any_kpi_fail": "KEEP_WATCH_WITH_GUARD",
            "insufficient_data": "HOLD_DATA_INSUFFICIENT",
        },
        "notes": [
            "This contract is governance-oriented and does not auto-bridge B-track into A-track.",
            "Human sign-off remains required for policy changes.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
