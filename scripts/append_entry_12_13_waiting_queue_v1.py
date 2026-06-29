#!/usr/bin/env python3
"""Append ENTRY_12/13 verification status to waiting queue log [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
LOG = ROOT / "docs/final/artifacts/waiting_queue_monthly_check_log.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", type=Path, default=LOG)
    args = ap.parse_args()

    gate = _load(GATE)
    p5 = _load(ROOT / "docs/final/artifacts/p5_manuscript_integrity_gate_v1_latest.json")
    row = {
        "schema": "waiting_queue_entry_12_13_verification_v1",
        "ts_utc": _utc(),
        "runner": "scripts/append_entry_12_13_waiting_queue_v1.py",
        "entries": ["ENTRY_12", "ENTRY_13"],
        "status": "p5_bench_relabel_pending_external_4q_anchor",
        "promotion_ok": gate.get("promotion_ok"),
        "promotion_pending_external": gate.get("promotion_pending_external"),
        "auto_verified_total": (gate.get("checks") or {}).get("scan_complete", {}).get("auto_verified_total"),
        "p5_manuscript_integrity_gate_ok": p5.get("gate_ok"),
        "note": (
            "ENTRY_12 mt_only (11Q5 retired); ENTRY_13 4Q83/4Q98b provisional only — "
            "DJD/QD col/line anchor for verified_anchor; no CROSS_REF draft mutation"
        ),
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "appended": True, "log": str(args.log.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
