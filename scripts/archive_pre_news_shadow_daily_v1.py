#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append pre_news_shadow_input snapshot to daily archive JSONL [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_LATEST = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"
DEFAULT_ARCHIVE = ROOT / "reports/pre_news_shadow_daily_archive_v1.jsonl"
DEFAULT_REPORT = ROOT / "reports/archive_pre_news_shadow_daily_v1_latest.json"
KST = ZoneInfo("Asia/Seoul")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _row_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("row_id") or ""),
        str(row.get("pub_date") or ""),
        str(row.get("headline") or row.get("title") or ""),
    )


def _load_archive_keys(path: Path) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    if not path.is_file():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        doc = json.loads(line)
        row = doc.get("row") if isinstance(doc.get("row"), dict) else doc
        if isinstance(row, dict):
            keys.add(_row_key(row))
    return keys


def archive_pre_news_snapshot(
    *,
    latest_path: Path,
    archive_path: Path,
    archive_kst: str | None = None,
) -> dict[str, Any]:
    archive_kst = (archive_kst or _today_kst())[:10]
    latest = json.loads(latest_path.read_text(encoding="utf-8-sig")) if latest_path.is_file() else {}
    rows = latest.get("rows") if isinstance(latest.get("rows"), list) else []
    existing = _load_archive_keys(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    appended = 0
    skipped = 0
    with archive_path.open("a", encoding="utf-8") as f:
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = _row_key(row)
            if key in existing:
                skipped += 1
                continue
            line = {
                "schema": "pre_news_shadow_archive_row_v1",
                "archive_kst": archive_kst,
                "archived_at_utc": _utc_now(),
                "snapshot_generated_at_utc": latest.get("generated_at_utc"),
                "row": row,
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
            existing.add(key)
            appended += 1

    return {
        "ok": True,
        "archive_kst": archive_kst,
        "latest_path": str(latest_path).replace("\\", "/"),
        "archive_path": str(archive_path).replace("\\", "/"),
        "snapshot_rows": len(rows),
        "appended": appended,
        "skipped_duplicates": skipped,
        "archive_unique_rows": len(existing),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--latest", type=Path, default=DEFAULT_LATEST)
    ap.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    ap.add_argument("--archive-kst", default=None)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    latest = args.latest if args.latest.is_absolute() else ROOT / args.latest
    archive = args.archive if args.archive.is_absolute() else ROOT / args.archive
    doc = archive_pre_news_snapshot(
        latest_path=latest,
        archive_path=archive,
        archive_kst=args.archive_kst,
    )
    rep = args.report if args.report.is_absolute() else ROOT / args.report
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
