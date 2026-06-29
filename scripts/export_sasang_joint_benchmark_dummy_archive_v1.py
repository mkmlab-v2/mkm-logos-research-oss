#!/usr/bin/env python3
"""Export dummy-tier rows from joint benchmark to archive JSONL (non-destructive) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
ARCHIVE = ROOT / "data/myeongni/sasang_saju_joint_benchmark_dummy_archive_v1.jsonl"
OUT = ROOT / "reports/sasang_joint_benchmark_dummy_archive_export_v1_latest.json"


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


def export(dataset: Path, archive: Path) -> dict[str, Any]:
    exported: list[str] = []
    rows: list[str] = []
    total = 0
    if dataset.is_file():
        for line in dataset.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            total += 1
            row = json.loads(line)
            if _is_dummy(row):
                rows.append(line)
                exported.append(str(row.get("person_id") or ""))

    archive.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        archive.write_text("\n".join(rows) + "\n", encoding="utf-8")
        export_ok = len(exported) >= 1
    elif archive.is_file():
        existing = [ln for ln in archive.read_text(encoding="utf-8").splitlines() if ln.strip()]
        exported = [
            str(json.loads(ln).get("person_id") or "")
            for ln in existing
        ]
        export_ok = len(exported) >= 1
    else:
        export_ok = False
    return {
        "schema": "sasang_joint_benchmark_dummy_archive_export_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_destructive": True,
        "benchmark_rows_total": total,
        "dummy_rows_exported": len(exported),
        "person_ids": exported,
        "archive_jsonl": str(archive.resolve()).replace("\\", "/"),
        "export_ok": export_ok,
        "reproduce": "py scripts/export_sasang_joint_benchmark_dummy_archive_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=BENCH)
    ap.add_argument("--archive", type=Path, default=ARCHIVE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = export(args.dataset, args.archive)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["export_ok"], "exported": doc["dummy_rows_exported"]}))
    return 0 if doc["export_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
