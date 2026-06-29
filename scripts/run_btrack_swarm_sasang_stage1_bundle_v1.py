#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 1 bundle: ATProto ingest → tier_a gate → optional Swarm×Sasang re-eval."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REAL_JSONL = ROOT / "data" / "btrack" / "swarm_sentiment_real_pit_v1.jsonl"
HOLD_OUT = ROOT / "reports/btrack_swarm_sasang_stage1_hold_v1_latest.json"
CLOSURE_OUT = ROOT / "reports/btrack_swarm_sasang_stage0_closure_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-krx-weekdays", type=int, default=30)
    ap.add_argument("--min-pairs", type=int, default=30)
    ap.add_argument("--date-from", type=str, default="2026-04-01")
    ap.add_argument("--date-to", type=str, default="2026-06-12")
    ap.add_argument(
        "--skip-live-collect",
        action="store_true",
        default=True,
        help="Default: do not call Bluesky API (use disk atproto raw only)",
    )
    ap.add_argument(
        "--collect-today",
        action="store_true",
        help="Run today's Bluesky probe before ingest (requires BSKY_* env)",
    )
    ap.add_argument(
        "--backfill",
        action="store_true",
        help="Paginate Bluesky search and write per-day raw JSONL by created_at",
    )
    ap.add_argument("--backfill-max-posts", type=int, default=2500)
    args = ap.parse_args()

    if args.collect_today:
        code = _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts/Invoke-BTrackAtprotoBlueskyProbe.ps1"),
            ]
        )
        if code != 0:
            return code

    if args.backfill:
        code = _run(
            [
                PY,
                str(ROOT / "scripts/backfill_atproto_sentiment_raw_by_created_date_v1.py"),
                "--date-from",
                args.date_from,
                "--date-to",
                args.date_to,
                "--calendar-mode",
                "krx_weekdays",
                "--max-posts",
                str(args.backfill_max_posts),
            ]
        )
        if code != 0:
            return code

    code = _run([PY, str(ROOT / "scripts/build_swarm_sentiment_from_atproto_v1.py")])
    if code != 0:
        return code

    if REAL_JSONL.is_file():
        code = _run(
            [
                PY,
                str(ROOT / "scripts/validate_swarm_sentiment_dummy.py"),
                "--jsonl",
                str(REAL_JSONL),
            ]
        )
        if code != 0:
            return code

    code = _run(
        [
            PY,
            str(ROOT / "scripts/check_btrack_swarm_tier_a_prereqs_v1.py"),
            "--min-krx-weekdays",
            str(args.min_krx_weekdays),
            "--jsonl",
            str(REAL_JSONL),
        ]
    )
    if code != 0 and code != 1:
        return code

    prereqs = _load_json(ROOT / "reports/btrack_swarm_tier_a_prereqs_v1_latest.json")
    tier_a_ready = bool(prereqs.get("tier_a_ready"))

    if tier_a_ready:
        code = _run(
            [
                PY,
                str(ROOT / "scripts/run_btrack_session_panel_swarm_corr_chain_v1.py"),
                "--date-from",
                args.date_from,
                "--date-to",
                args.date_to,
                "--calendar-mode",
                "krx_weekdays",
                "--swarm-jsonl",
                str(REAL_JSONL),
                "--ohlcv-csv",
                "research/market_data/kospi_daily_external_yf.csv",
                "--min-pairs",
                str(args.min_pairs),
                "--tag",
                "stage1_tier_a",
            ]
        )
        if code != 0:
            return code
        if HOLD_OUT.is_file():
            HOLD_OUT.unlink()
    else:
        hold = {
            "schema": "btrack_swarm_sasang_stage1_hold_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "send_gate": "HOLD",
            "stage": 1,
            "status": "HOLD_insufficient_tier_a_rows",
            "tier_a_ready": False,
            "min_krx_weekday_rows_required": args.min_krx_weekdays,
            "best_real_pit_rows": prereqs.get("best_real_pit_rows"),
            "real_jsonl": str(REAL_JSONL).replace("\\", "/"),
            "recommended_next": [
                "py scripts/run_btrack_swarm_sasang_stage1_bundle_v1.py --collect-today --backfill",
                "Or schedule: scripts/Register-BTrackAtprotoBlueskyProbeTask.ps1",
                "Backfill report: reports/btrack_atproto_backfill_v1_latest.json",
            ],
            "track_wall": {
                "fusion_pipeline_merge_allowed": False,
                "track_a_promotion": False,
                "live_trading": False,
            },
        }
        HOLD_OUT.parent.mkdir(parents=True, exist_ok=True)
        HOLD_OUT.write_text(json.dumps(hold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(HOLD_OUT.resolve()))
        print(f"stage1=HOLD tier_a_ready={tier_a_ready}")

    code = _run(
        [
            PY,
            str(ROOT / "scripts/build_btrack_swarm_sasang_stage0_closure_v1.py"),
            "--min-krx-weekdays",
            str(args.min_krx_weekdays),
        ]
    )
    if code != 0:
        return code
    return _run([PY, str(ROOT / "scripts/build_btrack_swarm_sasang_stage1_accumulation_v1.py")])


if __name__ == "__main__":
    raise SystemExit(main())
