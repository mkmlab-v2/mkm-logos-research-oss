#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 1 tier_a accumulation progress (read-only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_swarm_sasang_stage1_accumulation_v1_latest.json"


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def build(*, min_rows: int = 30) -> dict:
    prereqs = _load(ROOT / "reports/btrack_swarm_tier_a_prereqs_v1_latest.json")
    backfill = _load(ROOT / "reports/btrack_atproto_backfill_v1_latest.json")
    hold = _load(ROOT / "reports/btrack_swarm_sasang_stage1_hold_v1_latest.json")
    real = prereqs.get("best_real_pit_rows") or 0
    return {
        "schema": "btrack_swarm_sasang_stage1_accumulation_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "min_krx_weekday_rows": min_rows,
        "real_pit_rows": real,
        "progress_pct": round(100.0 * float(real) / float(min_rows), 1) if min_rows else 0.0,
        "tier_a_ready": bool(prereqs.get("tier_a_ready")),
        "scheduled_probe_task": "MKM_BTrack_AtprotoBluesky_Weekly",
        "backfill_summary": {
            "days_covered_on_disk": backfill.get("days_covered_on_disk"),
            "posts_fetched": backfill.get("posts_fetched"),
            "pit_rejected_after_cutoff": backfill.get("pit_rejected_after_cutoff"),
        }
        if backfill
        else None,
        "hold_status": hold.get("status"),
        "repro": (
            "py scripts/run_btrack_swarm_sasang_stage1_bundle_v1.py --collect-today --backfill"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-krx-weekdays", type=int, default=30)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    payload = build(min_rows=max(1, args.min_krx_weekdays))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out_json.resolve()))
    print(f"real_pit_rows={payload['real_pit_rows']}/{payload['min_krx_weekday_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
