#!/usr/bin/env python3
"""Load recent memory deltas and build current context 3 lines."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_MEMORY_JSONL = ART / "agent_memory_deltas_v1.jsonl"
DEFAULT_MEMORY_A = ART / "agent_memory_deltas_track_a_v1.jsonl"
DEFAULT_MEMORY_B = ART / "agent_memory_deltas_track_b_v1.jsonl"
DEFAULT_OUT = ART / "agent_memory_current_context_v1_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _sort_key(row: dict[str, Any]) -> str:
    return str(row.get("ts_utc") or "")


def _row_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("ts_utc") or ""),
        str(row.get("mission") or ""),
        str(row.get("state") or ""),
        str(row.get("source") or ""),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--memory-jsonl", type=Path, default=DEFAULT_MEMORY_JSONL)
    ap.add_argument("--memory-jsonl-a", type=Path, default=DEFAULT_MEMORY_A)
    ap.add_argument("--memory-jsonl-b", type=Path, default=DEFAULT_MEMORY_B)
    ap.add_argument("--recent-n", type=int, default=3)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_jsonl(args.memory_jsonl)
    rows_a = _read_jsonl(args.memory_jsonl_a)
    rows_b = _read_jsonl(args.memory_jsonl_b)
    merged_raw = rows + rows_a + rows_b
    dedup_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in merged_raw:
        dedup_map[_row_key(row)] = row
    merged = sorted(dedup_map.values(), key=_sort_key)
    recent = merged[-max(1, int(args.recent_n)) :]

    ctx: list[str] = []
    if not recent:
        ctx = ["mission=none", "state=none", "next=initialize_memory"]
    else:
        last = recent[-1]
        ctx = [
            f"mission={last.get('mission', 'unknown')} track={last.get('track', 'B')}",
            f"state={last.get('state', 'unknown')} risk={last.get('risk', 'unknown')}",
            f"next={last.get('next', 'continue')} confidence={last.get('confidence', 'C')}",
        ]

    out = {
        "schema": "agent_memory_current_context_v1",
        "generated_at_utc": _iso_now(),
        "recent_n": int(args.recent_n),
        "rows_seen": len(merged),
        "rows_seen_combined": len(rows),
        "rows_seen_track_a": len(rows_a),
        "rows_seen_track_b": len(rows_b),
        "rows_seen_before_dedup": len(merged_raw),
        "rows_seen_after_dedup": len(merged),
        "context_3line": ctx,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "rows_seen": len(merged)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
