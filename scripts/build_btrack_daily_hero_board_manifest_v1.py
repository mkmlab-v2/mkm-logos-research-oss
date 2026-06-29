#!/usr/bin/env python3
"""Build daily hero board manifest SSOT [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_daily_hero_board_manifest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    cal = _load(ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json")
    ev = _load(ROOT / "reports/btrack_daily_hero_board_eval_v1_latest.json")
    ins = _load(ROOT / "reports/btrack_daily_hero_board_evening_insight_v1_latest.json")
    chain = _load(ROOT / "reports/btrack_daily_hero_board_daily_chain_v1_latest.json")

    doc = {
        "schema": "btrack_daily_hero_board_manifest_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_mode": "daily_hero_board",
        "send_gate": "HOLD",
        "boundary_ack": True,
        "config": "data/commander/btrack_daily_hero_board_v1.json",
        "slot_count": len(cal.get("rows", [{}])[0].get("slots", {})) if cal.get("rows") else 5,
        "year_month": cal.get("year_month"),
        "as_of_kst": ev.get("as_of_kst"),
        "slot_metrics": ev.get("slot_metrics"),
        "evening_insight_triggered": ins.get("triggered"),
        "fail_count": ins.get("fail_count"),
        "artifact_pointers": {
            "calendar": "reports/btrack_daily_hero_board_calendar_v1_latest.json",
            "eval": "reports/btrack_daily_hero_board_eval_v1_latest.json",
            "evening_insight": "reports/btrack_daily_hero_board_evening_insight_v1_latest.json",
            "daily_chain": "reports/btrack_daily_hero_board_daily_chain_v1_latest.json",
            "kospi_eval": "reports/kospi_june2026_daily_prophecy_eval_latest.json",
            "general_prophecy_brier": "docs/final/artifacts/general_prophecy_brier_eval_latest.json",
        },
        "chains": [
            "scripts/run_btrack_daily_hero_board_chain_v1.py",
            "scripts/Invoke-KospiJune2026ProphecyLoop_v1.ps1",
        ],
        "last_chain_ok": chain.get("ok"),
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
