#!/usr/bin/env python3
"""Rebuild dummy archive from backup + existing archive (dedupe) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1_pre_prune_backup.jsonl"
ARCHIVE = ROOT / "data/myeongni/sasang_saju_joint_benchmark_dummy_archive_v1.jsonl"
OUT = ROOT / "reports/sasang_dummy_archive_weekly_snapshot_v1_latest.json"
MIN_ARCHIVE_ROWS = 3


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_dummy(row: dict[str, Any]) -> bool:
    pid = str(row.get("person_id") or "")
    disp = str(row.get("display_name") or "")
    if "dummy" in pid.lower() or "dummy" in disp.lower():
        return True
    if "DUMMYCSV" in pid or "DUMMYJSONL" in pid:
        return True
    if "[DUMMY]" in disp:
        return True
    return False


def _rows_from(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if _is_dummy(row):
            pid = str(row.get("person_id") or "")
            if pid:
                out[pid] = line
    return out


def rebuild() -> dict[str, Any]:
    merged: dict[str, str] = {}
    merged.update(_rows_from(ARCHIVE))
    merged.update(_rows_from(BACKUP))

    lines = list(merged.values())
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    snapshot_ok = len(lines) >= MIN_ARCHIVE_ROWS
    return {
        "schema": "sasang_dummy_archive_weekly_snapshot_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "archive_rows": len(lines),
        "person_ids": list(merged.keys()),
        "min_archive_rows": MIN_ARCHIVE_ROWS,
        "snapshot_ok": snapshot_ok,
        "archive_jsonl": str(ARCHIVE).replace("\\", "/"),
        "sources": {
            "backup": str(BACKUP).replace("\\", "/"),
            "prior_archive": str(ARCHIVE).replace("\\", "/"),
        },
        "reproduce": "py scripts/rebuild_sasang_dummy_archive_from_sources_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = rebuild()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["snapshot_ok"], "archive_rows": doc["archive_rows"]}))
    return 0 if doc["snapshot_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
