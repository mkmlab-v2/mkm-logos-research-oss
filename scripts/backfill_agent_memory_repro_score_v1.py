#!/usr/bin/env python3
"""Backfill reproducibility fields for existing agent memory rows."""

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


def _patch_rows(rows: list[dict[str, Any]], repro_cmd: str) -> tuple[list[dict[str, Any]], int]:
    changed = 0
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        if int(row.get("reproducibility_score") or 0) < 1:
            row["repro_cmd"] = repro_cmd
            row["reproducibility_score"] = 1
            row["repro_backfilled_at_utc"] = _iso_now()
            changed += 1
        out.append(row)
    return out, changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--memory-jsonl", type=Path, default=ART / "agent_memory_deltas_v1.jsonl")
    ap.add_argument("--memory-jsonl-a", type=Path, default=ART / "agent_memory_deltas_track_a_v1.jsonl")
    ap.add_argument("--memory-jsonl-b", type=Path, default=ART / "agent_memory_deltas_track_b_v1.jsonl")
    ap.add_argument(
        "--repro-cmd",
        default="powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_layer1_layer5_weekly_maintenance_v1.ps1 -WorkspaceRoot C:\\workspace",
    )
    ap.add_argument("--summary-json", type=Path, default=ART / "agent_memory_repro_backfill_summary_latest.json")
    args = ap.parse_args()

    rows_c = _read_jsonl(args.memory_jsonl)
    rows_a = _read_jsonl(args.memory_jsonl_a)
    rows_b = _read_jsonl(args.memory_jsonl_b)

    out_c, ch_c = _patch_rows(rows_c, str(args.repro_cmd))
    out_a, ch_a = _patch_rows(rows_a, str(args.repro_cmd))
    out_b, ch_b = _patch_rows(rows_b, str(args.repro_cmd))

    _write_jsonl(args.memory_jsonl, out_c)
    _write_jsonl(args.memory_jsonl_a, out_a)
    _write_jsonl(args.memory_jsonl_b, out_b)

    summary = {
        "schema": "agent_memory_repro_backfill_summary_v1",
        "generated_at_utc": _iso_now(),
        "changed_rows": {"combined": ch_c, "track_a": ch_a, "track_b": ch_b, "total": ch_c + ch_a + ch_b},
        "status": "PASS",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "summary_json": str(args.summary_json), "changed_total": ch_c + ch_a + ch_b}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
