#!/usr/bin/env python3
"""Mark specific memory rows as resolved for review closure."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _resolve_in_file(path: Path, target_source: str, note: str) -> int:
    rows = _read_jsonl(path)
    changed = 0
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        if str(row.get("source") or "") == target_source:
            row["review_status"] = "resolved"
            row["resolved_at_utc"] = _iso_now()
            row["resolution_note"] = note
            changed += 1
        out.append(row)
    _write_jsonl(path, out)
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-source", required=True)
    ap.add_argument("--resolution-note", default="manual review resolved")
    ap.add_argument("--memory-jsonl", type=Path, default=ART / "agent_memory_deltas_v1.jsonl")
    ap.add_argument("--memory-jsonl-a", type=Path, default=ART / "agent_memory_deltas_track_a_v1.jsonl")
    ap.add_argument("--memory-jsonl-b", type=Path, default=ART / "agent_memory_deltas_track_b_v1.jsonl")
    ap.add_argument("--summary-json", type=Path, default=ART / "agent_memory_resolution_summary_latest.json")
    args = ap.parse_args()

    c1 = _resolve_in_file(args.memory_jsonl, args.target_source, args.resolution_note)
    c2 = _resolve_in_file(args.memory_jsonl_a, args.target_source, args.resolution_note)
    c3 = _resolve_in_file(args.memory_jsonl_b, args.target_source, args.resolution_note)
    total = c1 + c2 + c3

    summary = {
        "schema": "agent_memory_resolution_summary_v1",
        "generated_at_utc": _iso_now(),
        "target_source": args.target_source,
        "changed_rows": {
            "combined": c1,
            "track_a": c2,
            "track_b": c3,
            "total": total,
        },
        "status": "PASS" if total > 0 else "NO_MATCH",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "summary_json": str(args.summary_json), "status": summary["status"], "changed_total": total}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
