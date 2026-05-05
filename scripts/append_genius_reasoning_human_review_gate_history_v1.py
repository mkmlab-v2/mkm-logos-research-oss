#!/usr/bin/env python3
"""Append genius human review gate snapshot to history log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_GATE = ART / "genius_reasoning_human_review_gate_latest.json"
DEFAULT_HISTORY = ART / "genius_reasoning_human_review_gate_history_log.jsonl"


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
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--source", type=str, default="operational")
    args = ap.parse_args()

    gate = _read_json(args.gate_json)
    current = gate.get("current") if isinstance(gate.get("current"), dict) else {}
    row = {
        "schema": "genius_reasoning_human_review_gate_history_row_v1",
        "ts_utc": _iso_now(),
        "status": gate.get("status"),
        "reasons": gate.get("reasons"),
        "pending_rows": current.get("pending_rows"),
        "pending_ratio": current.get("pending_ratio"),
        "pending_age_days": current.get("pending_age_days"),
        "source": str(args.source or "operational"),
    }
    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "history_jsonl": str(args.history_jsonl).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
