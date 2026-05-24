#!/usr/bin/env python3
"""Write dual-lane prophecy hit-rate SSOT pointer manifest (Phase A)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_hit_rate_ssot_v1 import (  # noqa: E402
    DAILY_OPERATIONAL,
    HEADLINE_KPI,
    OP29B_STRATEGIC_SYNC,
    REL_DAILY_OPERATIONAL,
    REL_HEADLINE_KPI,
    REL_OP29B_STRATEGIC_SYNC,
    REL_SSOT_POINTER,
    SSOT_POINTER,
)

SCHEMA = "prophecy_hit_rate_ssot_pointer_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lane_snapshot(
    path: Path,
    *,
    rel_path: str,
    lane_id: str,
    role: str,
    writers: list[str],
    readers_note: str,
) -> dict[str, Any]:
    snap: dict[str, Any] = {
        "lane_id": lane_id,
        "role": role,
        "relative_path": rel_path,
        "path": str(path),
        "exists": path.is_file(),
        "writers": writers,
        "readers_note": readers_note,
    }
    if path.is_file():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            metrics = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
            snap["generated_at_utc"] = doc.get("generated_at_utc")
            snap["price_directional_hit_rate"] = metrics.get("price_directional_hit_rate")
            snap["n_evaluated"] = metrics.get("n_evaluated")
            snap["headline_promotion_v1"] = doc.get("headline_promotion_v1")
        except (json.JSONDecodeError, OSError):
            snap["parse_error"] = True
    return snap


def _op29b_snapshot() -> dict[str, Any]:
    snap: dict[str, Any] = {
        "lane_id": "strategic_observation_op29b",
        "role": "commander_observation_not_formal_promotion",
        "relative_path": REL_OP29B_STRATEGIC_SYNC,
        "path": str(OP29B_STRATEGIC_SYNC),
        "exists": OP29B_STRATEGIC_SYNC.is_file(),
        "writers": ["scripts/sync_op29b_prophecy_gates_headline_v1.py"],
    }
    if OP29B_STRATEGIC_SYNC.is_file():
        try:
            doc = json.loads(OP29B_STRATEGIC_SYNC.read_text(encoding="utf-8"))
            hs = doc.get("headline_status") if isinstance(doc.get("headline_status"), dict) else {}
            gs = doc.get("gates_summary") if isinstance(doc.get("gates_summary"), dict) else {}
            snap["generated_at_utc"] = doc.get("generated_at_utc")
            snap["headline_status_rate"] = hs.get("rate")
            snap["combined_all_passed"] = gs.get("combined_all_passed")
        except (json.JSONDecodeError, OSError):
            snap["parse_error"] = True
    return snap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=SSOT_POINTER)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "policy": {
            "headline_kpi_write": "promote_op28_headline_kpi_v1 or eval_prophecy_hit_rate_v1 with --allow-headline-write only",
            "daily_operational_write": "run_daily_prophecy_eval_and_report.ps1 and causal daily chain",
            "track_a_live_auto_merge": False,
        },
        "lanes": {
            "headline_kpi": _lane_snapshot(
                HEADLINE_KPI,
                rel_path=REL_HEADLINE_KPI,
                lane_id="headline_kpi_commander",
                role="commander_approved_active_kpi",
                writers=["scripts/promote_op28_headline_kpi_v1.py"],
                readers_note=(
                    "Commander headline SSOT: may be all-rows OR ACTIVE-gated after promote_op28. "
                    "Do not confuse with daily_operational (30d) or op29b observation lane. "
                    "ACTIVE gate sweep (no auto-promote): reports/prophecy_btrack_headline_gates_recommended_chain_v1_latest.json"
                ),
            ),
            "daily_operational": _lane_snapshot(
                DAILY_OPERATIONAL,
                rel_path=REL_DAILY_OPERATIONAL,
                lane_id="daily_operational_sliding",
                role="scheduled_short_window_eval",
                writers=[
                    "scripts/run_daily_prophecy_eval_and_report.ps1",
                    "scripts/run_daily_prophecy_then_pre_news_v1.ps1 (causal block)",
                    "scripts/eval_prophecy_hit_rate_v1.py (default output)",
                ],
                readers_note="Causal guard, health status, promotion gates inputs when refreshed from daily chain",
            ),
            "strategic_observation_op29b": _op29b_snapshot(),
        },
        "relative_paths": {
            "headline_kpi": REL_HEADLINE_KPI,
            "daily_operational": REL_DAILY_OPERATIONAL,
            "ssot_pointer": REL_SSOT_POINTER,
            "op29b_strategic_sync": REL_OP29B_STRATEGIC_SYNC,
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
