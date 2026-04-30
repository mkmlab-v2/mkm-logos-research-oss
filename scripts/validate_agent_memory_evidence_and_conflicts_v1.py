#!/usr/bin/env python3
"""Validate memory JSONL evidence and conflict flags."""

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
DEFAULT_OUT = ART / "agent_memory_validation_latest.json"


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


def _row_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("ts_utc") or ""),
        str(row.get("mission") or ""),
        str(row.get("state") or ""),
        str(row.get("source") or ""),
    )


def _evidence_exists(row: dict[str, Any]) -> bool:
    if "evidence_exists_all" in row:
        return bool(row.get("evidence_exists_all"))
    ev = row.get("evidence_path")
    if not isinstance(ev, list) or not ev:
        return False
    try:
        return all(Path(str(p)).is_file() for p in ev)
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--memory-jsonl", type=Path, default=DEFAULT_MEMORY_JSONL)
    ap.add_argument("--memory-jsonl-a", type=Path, default=DEFAULT_MEMORY_A)
    ap.add_argument("--memory-jsonl-b", type=Path, default=DEFAULT_MEMORY_B)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows_combined = _read_jsonl(args.memory_jsonl)
    rows_a = _read_jsonl(args.memory_jsonl_a)
    rows_b = _read_jsonl(args.memory_jsonl_b)
    dedup: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for r in rows_combined + rows_a + rows_b:
        dedup[_row_key(r)] = r
    rows = list(dedup.values())
    evidence_missing = 0
    conflicts = 0
    confidence_c = 0
    resolved_rows = 0
    for r in rows:
        if str(r.get("review_status") or "") == "resolved":
            resolved_rows += 1
            continue
        if not _evidence_exists(r):
            evidence_missing += 1
        conflict = bool(((r.get("conflict_flags") or {}).get("has_conflict")))
        if conflict:
            conflicts += 1
        if str(r.get("confidence") or "") == "C":
            confidence_c += 1

    out = {
        "schema": "agent_memory_validation_v1",
        "generated_at_utc": _iso_now(),
        "memory_jsonl": str(args.memory_jsonl).replace("\\", "/"),
        "memory_jsonl_a": str(args.memory_jsonl_a).replace("\\", "/"),
        "memory_jsonl_b": str(args.memory_jsonl_b).replace("\\", "/"),
        "summary": {
            "total_rows": len(rows),
            "rows_combined": len(rows_combined),
            "rows_track_a": len(rows_a),
            "rows_track_b": len(rows_b),
            "evidence_missing_rows": evidence_missing,
            "conflict_rows": conflicts,
            "confidence_c_rows": confidence_c,
            "resolved_rows": resolved_rows,
        },
        "status": "PASS" if conflicts == 0 and evidence_missing == 0 else "HOLD_REVIEW",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "status": out["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
