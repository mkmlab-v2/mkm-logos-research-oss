#!/usr/bin/env python3
"""Split MISSION_LOG.md: keep slim ops board; move bulk history to MISSION_LOG.old.md.

Does not read via agent — run locally:
  py scripts/split_mission_log_old_v1.py --dry-run
  py scripts/split_mission_log_old_v1.py
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "MISSION_LOG.md"
OLD = ROOT / "MISSION_LOG.old.md"
BACKUP = ROOT / "MISSION_LOG.pre_split_backup.md"

KEEP_START = "## 🚀 전술 작전 보드"
# First top-level ## after keep block that starts bulk history (exclusive).
# First matching line after KEEP_START ends the slim SSOT slice (exclusive).
KEEP_END_MARKERS = (
    "### 🔗 채팅 SSOT",
    "## COMP-UNIV-BENCH",
    "## Active —",
    "## Active -",
    "## Planned —",
    "## ARCHIVE",
    "## MISSION_LOG ARCHIVE",
    "## Oracle — 자동진행",
    "## Oracle - 자동진행",
    "## MS — 자동진행",
    "## 압축 — 자동진행",
    "## 자동진행 (",
    "## 자동진행(",
    "## [OPERATION_MODE",
    "## 융합 보드",
    "## 일일 일정 SSOT",
    "## 주간 일정 SSOT",
    "## Completed (",
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_keep_range(lines: list[str]) -> tuple[int, int]:
    start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(KEEP_START):
            start = i
            break
    if start < 0:
        raise SystemExit(f"KEEP_START not found: {KEEP_START!r}")

    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if any(stripped.startswith(m) for m in KEEP_END_MARKERS):
            end = i
            break

    return start, end


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-keep-lines", type=int, default=0, help="Cap keep slice (0=no cap).")
    args = ap.parse_args()

    if not LOG.is_file():
        raise SystemExit(f"Missing: {LOG}")

    text = LOG.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    start, end = _find_keep_range(lines)
    if args.max_keep_lines > 0:
        end = min(end, start + args.max_keep_lines)

    prefix = lines[:start]
    keep = lines[start:end]
    suffix = lines[end:]

    header = (
        "# MISSION_LOG — 운영 작전 보드 (슬림 · SSOT)\n"
        f"\n"
        f"> **분리:** {_utc_stamp()} · 구간·자동진행·ARCHIVE → [`MISSION_LOG.old.md`](MISSION_LOG.old.md)  \n"
        f"> **재개:** `@MISSION_LOG.md` + 「미션로그 이어서」 — **본 파일 상단만** 갱신.\n"
        f"\n"
    )
    old_header = (
        "# MISSION_LOG.old — 아카이브 (비-SSOT · 참고)\n"
        f"\n"
        f"> **생성:** {_utc_stamp()} · `scripts/split_mission_log_old_v1.py`  \n"
        f"> **운영 SSOT는** 루트 `MISSION_LOG.md` **작전 보드 블록만**.\n"
        f"\n"
        "---\n\n"
    )

    old_body: list[str] = []
    if prefix:
        old_body.append("## (이전 상단 — 작전 보드 이전)\n\n")
        old_body.extend(prefix)
        old_body.append("\n---\n\n")
    old_body.append("## (작전 보드 이후 — 아카이브·자동진행 등)\n\n")
    old_body.extend(suffix)

    new_log = header + "".join(keep)
    new_old = old_header + "".join(old_body)

    print(f"source_lines={len(lines)} keep={start}-{end} ({end-start} lines)")
    print(f"old_parts: prefix={len(prefix)} suffix={len(suffix)}")
    print(f"new MISSION_LOG.md ~{len(new_log.splitlines())} lines")
    print(f"new MISSION_LOG.old.md ~{len(new_old.splitlines())} lines")

    if args.dry_run:
        return 0

    if BACKUP.is_file():
        pass
    shutil.copy2(LOG, BACKUP)
    print(f"backup: {BACKUP}")

    LOG.write_text(new_log if new_log.endswith("\n") else new_log + "\n", encoding="utf-8")
    OLD.write_text(new_old if new_old.endswith("\n") else new_old + "\n", encoding="utf-8")
    print(f"WROTE: {LOG}")
    print(f"WROTE: {OLD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
