#!/usr/bin/env python3
"""Append weekly ops report snapshot to history log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_WEEKLY = ART / "layer1_layer5_weekly_ops_report_latest.json"
DEFAULT_LOG = ART / "layer1_layer5_weekly_ops_history_log.jsonl"


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
    ap.add_argument("--weekly-report-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    weekly = _read_json(args.weekly_report_json)
    summary = weekly.get("summary") if isinstance(weekly.get("summary"), dict) else {}
    row = {
        "schema": "layer1_layer5_weekly_ops_history_row_v1",
        "ts_utc": _iso_now(),
        "source": str(args.weekly_report_json).replace("\\", "/"),
        "overall_status": weekly.get("overall_status"),
        "base_weekly_status": weekly.get("base_overall_status")
        or summary.get("base_weekly_status")
        or weekly.get("overall_status"),
        "emotion_preflight_decision": summary.get("emotion_preflight_decision"),
    }
    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "history_jsonl": str(args.history_jsonl), "overall_status": row["overall_status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
