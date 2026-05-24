#!/usr/bin/env python3
"""Apply fee-bleed guard: cap max_trades_per_day (live ops). No prophecy routing."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RISK_PATH = ROOT / "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json"
TRADE_24H = ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/cursor_trade_history_latest_24h.json"
DEFAULT_REPORT = ROOT / "reports/live_fee_guard_applied_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _trade_stats(path: Path) -> dict[str, Any]:
    doc = _load(path) if path.is_file() else {}
    rows = list(doc.get("treatment") or []) + list(doc.get("control") or [])
    realized = commission = 0.0
    for r in rows:
        try:
            realized += float(r.get("realized_pnl") or 0)
            commission += float(r.get("commission") or 0)
        except (TypeError, ValueError):
            pass
    return {"trade_count_24h": len(rows), "net_pnl_usdt": round(realized - commission, 6)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-trades-per-day", type=int, default=int(os.environ.get("MKM_FEE_GUARD_MAX_TRADES_PER_DAY", "6")))
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not RISK_PATH.is_file():
        print(f"MISSING: {RISK_PATH}")
        return 2

    before = _load(RISK_PATH)
    prev_max = int(before.get("max_trades_per_day") or 99)
    new_max = min(prev_max, max(1, args.max_trades_per_day))

    after = dict(before)
    after["max_trades_per_day"] = new_max
    after["maker_only_level"] = "strict" if str(before.get("maker_only_level") or "") != "strict" else before.get("maker_only_level")
    note = "fee_guard_recommended_posture_v1: cap trade frequency to reduce commission bleed"
    prior = str(after.get("notes") or "")
    if note not in prior:
        after["notes"] = f"{prior} | {note}".strip(" |")

    report = {
        "schema": "live_fee_guard_applied_v1",
        "generated_at_utc": _utc(),
        "research_only": False,
        "dry_run": args.dry_run,
        "prophecy_routing_changed": False,
        "risk_profile_path": str(RISK_PATH.relative_to(ROOT)).replace("\\", "/"),
        "before": {"max_trades_per_day": prev_max, "maker_only_level": before.get("maker_only_level")},
        "after": {"max_trades_per_day": new_max, "maker_only_level": after.get("maker_only_level")},
        "live_24h": _trade_stats(TRADE_24H),
        "operator_note": "Shadow prophecy unchanged; only trade-frequency cap tightened.",
    }

    if not args.dry_run:
        bak = RISK_PATH.with_suffix(".json.bak_fee_guard")
        shutil.copy2(RISK_PATH, bak)
        RISK_PATH.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["backup_path"] = str(bak.relative_to(ROOT)).replace("\\", "/")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.report.resolve()}")
    print(f"max_trades_per_day: {prev_max} -> {new_max} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
