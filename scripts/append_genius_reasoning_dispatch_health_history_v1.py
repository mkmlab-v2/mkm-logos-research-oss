#!/usr/bin/env python3
"""Append dispatch health snapshot for genius governance alerts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_ALERT_DISPATCH = ART / "genius_reasoning_benchmark_alert_dispatch_latest.json"
DEFAULT_REVIEW_DISPATCH = ART / "genius_reasoning_human_review_gate_dispatch_latest.json"
DEFAULT_TREND_DISPATCH = ART / "genius_reasoning_human_review_gate_trend_dispatch_latest.json"
DEFAULT_HISTORY = ART / "genius_reasoning_dispatch_health_history_log.jsonl"


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


def _extract(prefix: str, doc: dict[str, Any]) -> dict[str, Any]:
    decision = doc.get("decision") if isinstance(doc.get("decision"), dict) else {}
    dispatch = doc.get("dispatch") if isinstance(doc.get("dispatch"), dict) else {}
    return {
        f"{prefix}_should_dispatch": bool(decision.get("should_dispatch")),
        f"{prefix}_webhook_configured": bool(decision.get("webhook_configured")),
        f"{prefix}_dispatch_status": dispatch.get("status"),
        f"{prefix}_dispatch_reason": dispatch.get("reason"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alert-dispatch-json", type=Path, default=DEFAULT_ALERT_DISPATCH)
    ap.add_argument("--human-review-dispatch-json", type=Path, default=DEFAULT_REVIEW_DISPATCH)
    ap.add_argument("--human-review-trend-dispatch-json", type=Path, default=DEFAULT_TREND_DISPATCH)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    args = ap.parse_args()

    row = {
        "schema": "genius_reasoning_dispatch_health_history_row_v1",
        "ts_utc": _iso_now(),
    }
    row.update(_extract("benchmark_alert", _read_json(args.alert_dispatch_json)))
    row.update(_extract("human_review_gate", _read_json(args.human_review_dispatch_json)))
    row.update(_extract("human_review_trend", _read_json(args.human_review_trend_dispatch_json)))

    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "history_jsonl": str(args.history_jsonl).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
