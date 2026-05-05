#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.9}
# Balance: 89
# Purpose: Append genius governance scheduler health snapshot to history JSONL.
# Keywords: health history, scheduler, jsonl, governance
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_HEALTH = ART / "genius_governance_scheduler_health_check_latest.json"
DEFAULT_HISTORY = ART / "genius_governance_scheduler_health_history_log.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--health-json", type=Path, default=DEFAULT_HEALTH)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    args = ap.parse_args()

    health = _read_json(args.health_json)
    summary = health.get("summary") if isinstance(health.get("summary"), dict) else {}
    row = {
        "schema": "genius_governance_scheduler_health_history_row_v1",
        "ts_utc": _iso_now(),
        "health_status": str(health.get("status") or "UNKNOWN").upper(),
        "tasks_ok": bool(summary.get("tasks_ok")),
        "monthly_suite_pass": bool(summary.get("monthly_suite_pass")),
        "unified_dashboard_go": bool(summary.get("unified_dashboard_go")),
    }
    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "history_jsonl": str(args.history_jsonl).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
