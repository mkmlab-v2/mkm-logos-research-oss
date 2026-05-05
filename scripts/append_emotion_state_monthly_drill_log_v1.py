#!/usr/bin/env python3
"""Append emotion-state monthly promotion drill result to persistent log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRILL_RESULT = ROOT / "docs" / "final" / "artifacts" / "emotion_state_monthly_promotion_drill_summary_latest.json"
DEFAULT_LOG = ROOT / "reports" / "emotion_state_monthly_drill_log.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "emotion_state_monthly_drill_log_summary_latest.json"


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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drill-result-json", type=Path, default=DEFAULT_DRILL_RESULT)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    drill = _read_json(args.drill_result_json)
    row = {
        "ts_utc": _iso_now(),
        "schema": "emotion_state_monthly_drill_log_row_v1",
        "source": str(args.drill_result_json).replace("\\", "/"),
        "drill_passed": bool(drill.get("drill_passed")),
        "approve_case_passed": bool((drill.get("approve_case") or {}).get("passed")),
        "reject_case_passed": bool((drill.get("reject_case") or {}).get("passed")),
    }
    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.log_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    rows = _read_jsonl(args.log_jsonl)
    total = len(rows)
    fail_count = sum(1 for r in rows if not bool(r.get("drill_passed")))
    summary = {
        "schema": "emotion_state_monthly_drill_log_summary_v1",
        "log_jsonl": str(args.log_jsonl).replace("\\", "/"),
        "total_entries": total,
        "failed_entries": fail_count,
        "latest": row,
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "total_entries": total, "failed_entries": fail_count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
