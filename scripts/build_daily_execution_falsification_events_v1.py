#!/usr/bin/env python3
"""Build/append daily execution falsification events for lens penalty shadow."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_INPUT = REPORTS / "daily_execution_falsification_input_latest.json"
DEFAULT_EVENTS = REPORTS / "daily_execution_insight_falsification_log.jsonl"
DEFAULT_OUT = ART / "daily_execution_falsification_events_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _normalize_result(pred: str, actual: str, explicit: str) -> str:
    exp = explicit.strip().upper()
    if exp in {"HIT", "FAIL"}:
        return exp
    if not pred or not actual:
        return "UNKNOWN"
    return "HIT" if pred == actual else "FAIL"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--events-jsonl", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    src = _read_json(args.input_json)
    entries = src.get("entries") if isinstance(src.get("entries"), list) else []

    summary: dict[str, Any] = {
        "schema": "daily_execution_falsification_events_v1",
        "generated_at_utc": _now(),
        "input_json": str(args.input_json.resolve()).replace("\\", "/"),
        "events_jsonl": str(args.events_jsonl.resolve()).replace("\\", "/"),
        "appended_count": 0,
        "hit_count": 0,
        "fail_count": 0,
        "unknown_count": 0,
        "status": "NO_INPUT",
        "note": "",
    }

    if not src:
        summary["status"] = "NO_INPUT"
        summary["note"] = "input_json_missing_or_invalid"
    elif not entries:
        summary["status"] = "NO_ENTRIES"
        summary["note"] = "entries_missing_or_empty"
    else:
        args.events_jsonl.parent.mkdir(parents=True, exist_ok=True)
        appended: list[dict[str, Any]] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            lens_id = str(item.get("lens_id") or "").strip()
            pred = str(item.get("prediction_label") or "").strip().upper()
            actual = str(item.get("actual_label") or "").strip().upper()
            result = _normalize_result(pred, actual, str(item.get("result") or ""))
            if not lens_id:
                continue
            row = {
                "schema": "daily_execution_falsification_event_v1",
                "timestamp_utc": _now(),
                "date_utc": str(src.get("date_utc") or ""),
                "lens_id": lens_id,
                "prediction_label": pred,
                "actual_label": actual,
                "result": result,
                "source": str(src.get("source") or "operator_input"),
            }
            appended.append(row)

        with args.events_jsonl.open("a", encoding="utf-8") as fp:
            for row in appended:
                fp.write(json.dumps(row, ensure_ascii=False) + "\n")

        summary["appended_count"] = len(appended)
        summary["hit_count"] = sum(1 for r in appended if r["result"] == "HIT")
        summary["fail_count"] = sum(1 for r in appended if r["result"] == "FAIL")
        summary["unknown_count"] = sum(1 for r in appended if r["result"] not in {"HIT", "FAIL"})
        summary["status"] = "APPENDED" if appended else "NO_VALID_ROWS"
        summary["note"] = "ok" if appended else "no_valid_rows_after_validation"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"status={summary['status']}; appended={summary['appended_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
