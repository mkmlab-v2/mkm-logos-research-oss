#!/usr/bin/env python3
"""Append P9 final Bible rail closure row to waiting queue log [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/logos_bible_rail_completion_gate_v1_latest.json"
LOG = ROOT / "docs/final/artifacts/waiting_queue_monthly_check_log.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", type=Path, default=LOG)
    args = ap.parse_args()

    gate = _load(GATE)
    row = {
        "schema": "waiting_queue_bible_rail_p9_final_v1",
        "ts_utc": _utc(),
        "runner": "scripts/append_bible_rail_p9_final_waiting_queue_v1.py",
        "entries": ["ENTRY_12", "ENTRY_13"],
        "status": gate.get("bible_rail_status") or "incomplete",
        "completion_gate_ok": gate.get("gate_ok"),
        "send_gate": gate.get("send_gate") or "HOLD",
        "human_gates_completed": gate.get("human_gates_completed") or [],
        "future_research_open": gate.get("future_research_open") or [],
        "note": "P9 final: CROSS_REF ENTRY_12/13 applied; verified_anchor gap documented; JSONL bench skipped",
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "status": row["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
