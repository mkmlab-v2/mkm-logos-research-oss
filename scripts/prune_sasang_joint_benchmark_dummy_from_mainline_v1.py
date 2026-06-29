#!/usr/bin/env python3
"""Prune dummy-tier rows from mainline benchmark (archive must exist first) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
ARCHIVE = ROOT / "data/myeongni/sasang_saju_joint_benchmark_dummy_archive_v1.jsonl"
BACKUP = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1_pre_prune_backup.jsonl"
OUT = ROOT / "reports/sasang_joint_benchmark_mainline_prune_v1_latest.json"


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


def _count_archive_dummy(archive: Path) -> int:
    if not archive.is_file():
        return 0
    n = 0
    for line in archive.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n += 1
    return n


def prune(*, apply: bool) -> dict[str, Any]:
    if not BENCH.is_file():
        return {"prune_ok": False, "error": "missing_benchmark"}
    archive_dummy = _count_archive_dummy(ARCHIVE)
    if archive_dummy < 1:
        return {"prune_ok": False, "error": "archive_missing_or_empty"}

    kept: list[str] = []
    removed_ids: list[str] = []
    for line in BENCH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if _is_dummy(row):
            removed_ids.append(str(row.get("person_id") or ""))
        else:
            kept.append(line)

    already_pruned = len(removed_ids) == 0 and len(kept) >= 5
    prune_ok = (len(removed_ids) >= 1 and len(kept) >= 5) or (already_pruned and archive_dummy >= 1)
    applied = False
    if apply and prune_ok and len(removed_ids) >= 1:
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BENCH, BACKUP)
        BENCH.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        applied = True

    return {
        "schema": "sasang_joint_benchmark_mainline_prune_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "archive_dummy_rows": archive_dummy,
        "mainline_rows_before": len(kept) + len(removed_ids),
        "mainline_rows_after": len(kept),
        "dummy_rows_removed": len(removed_ids),
        "removed_person_ids": removed_ids,
        "prune_ok": prune_ok,
        "already_pruned": already_pruned,
        "applied": applied,
        "backup_path": str(BACKUP).replace("\\", "/") if applied else None,
        "archive_jsonl": str(ARCHIVE).replace("\\", "/"),
        "reproduce": "py scripts/prune_sasang_joint_benchmark_dummy_from_mainline_v1.py --apply",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = prune(apply=args.apply)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc.get("prune_ok"),
                "applied": doc.get("applied"),
                "removed": doc.get("dummy_rows_removed"),
            }
        )
    )
    return 0 if doc.get("prune_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
