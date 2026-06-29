#!/usr/bin/env python3
"""Append P11 ENTRY_01-16 sequential rail row to waiting queue log [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEQ_GATE = ROOT / "docs/final/artifacts/cross_ref_dss_entry_sequential_gate_v1_latest.json"
WQ_GATE = ROOT / "docs/final/artifacts/cross_ref_waiting_queue_consolidated_gate_v1_latest.json"
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

    seq = _load(SEQ_GATE)
    wq = _load(WQ_GATE)
    row = {
        "schema": "waiting_queue_bible_rail_p11_sequential_v1",
        "ts_utc": _utc(),
        "runner": "scripts/append_bible_rail_p11_sequential_waiting_queue_v1.py",
        "entries": ["ENTRY_01", "ENTRY_02", "ENTRY_03", "ENTRY_04", "ENTRY_05", "ENTRY_06", "ENTRY_07", "ENTRY_08", "ENTRY_09", "ENTRY_10", "ENTRY_11", "ENTRY_12", "ENTRY_13", "ENTRY_14", "ENTRY_15", "ENTRY_16"],
        "sequential_rail_status": seq.get("sequential_rail_status"),
        "sequential_gate_ok": seq.get("gate_ok"),
        "waiting_queue_status": wq.get("waiting_queue_status"),
        "waiting_queue_gate_ok": wq.get("gate_ok"),
        "waiting_queue_open": ["ENTRY_07", "ENTRY_08", "ENTRY_16"],
        "send_gate": "HOLD",
        "note": "P11 full sequential rail; ENTRY_07/08 comparandum hold; ENTRY_16 manual review lock without CROSS_REF mutation",
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "sequential_rail_status": row["sequential_rail_status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
