#!/usr/bin/env python3
"""Build unified validation packet from C queue artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"

COMPARE = PILOT / "symbol_c_validation_queue_compare_latest.json"
CHECK_STABLE = PILOT / "symbol_c_validation_checklist_stable_latest.json"
CHECK_EXPL = PILOT / "symbol_c_validation_checklist_exploratory_latest.json"
OUT = PILOT / "symbol_c_validation_packet_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _top_task_symbols(checklist: dict[str, Any], k: int = 10) -> list[str]:
    tasks = checklist.get("tasks", [])
    if not isinstance(tasks, list):
        return []
    out: list[str] = []
    for row in tasks[:k]:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "")).strip()
        if symbol:
            out.append(symbol)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build symbol C validation packet")
    ap.add_argument("--compare-json", default=str(COMPARE))
    ap.add_argument("--checklist-stable", default=str(CHECK_STABLE))
    ap.add_argument("--checklist-exploratory", default=str(CHECK_EXPL))
    ap.add_argument("--out-json", default=str(OUT))
    args = ap.parse_args()

    compare_path = _abs(args.compare_json)
    stable_path = _abs(args.checklist_stable)
    expl_path = _abs(args.checklist_exploratory)
    out_path = _abs(args.out_json)
    for p in (compare_path, stable_path, expl_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    compare = _jread(compare_path)
    stable = _jread(stable_path)
    expl = _jread(expl_path)

    packet = {
        "schema": "btrack_symbol_c_validation_packet_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "compare_json": str(compare_path),
            "checklist_stable_json": str(stable_path),
            "checklist_exploratory_json": str(expl_path),
        },
        "snapshot": {
            "stable_task_count": int(stable.get("task_count", 0) or 0),
            "exploratory_task_count": int(expl.get("task_count", 0) or 0),
            "compare_delta_count": int(compare.get("delta", {}).get("count", 0) or 0),
            "compare_delta_avg_score": float(compare.get("delta", {}).get("avg_score", 0.0) or 0.0),
            "top_overlap_rate": float(compare.get("top_overlap", {}).get("rate", 0.0) or 0.0),
        },
        "priority_preview": {
            "stable_top10_symbols": _top_task_symbols(stable, 10),
            "exploratory_top10_symbols": _top_task_symbols(expl, 10),
        },
        "ops_note": "Use checklist tasks for scholarly/theory review queue; this packet is operational status only.",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol C validation packet generated")
    print(f"out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
