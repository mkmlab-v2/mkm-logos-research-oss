#!/usr/bin/env python3
"""Cap MISSION_LOG session blockquote lines; overflow → MISSION_LOG.sessions.md.

Default keep newest 14 session lines. Meta blockquotes (분리/재개/세션 아카이브) stay.

  py scripts/rotate_mission_log_sessions_v1.py --dry-run
  py scripts/rotate_mission_log_sessions_v1.py --max-keep 14
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "MISSION_LOG.md"
SESSIONS_ARCHIVE = ROOT / "MISSION_LOG.sessions.md"
KEEP_START = "## 🚀 전술 작전 보드"

SESSION_RE = re.compile(r"^\>\s+\*\*세션\s+갱신")
META_ARCHIVE_RE = re.compile(r"^\>\s+\*\*세션\s+아카이브:")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_board_start(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if line.strip().startswith(KEEP_START):
            return i
    return -1


def parse_session_prefix(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (meta_lines, session_lines, rest_from_board)."""
    board = _find_board_start(lines)
    if board < 0:
        raise ValueError(f"{KEEP_START!r} not found in MISSION_LOG.md")

    prefix = lines[:board]
    meta: list[str] = []
    sessions: list[str] = []
    for line in prefix:
        if SESSION_RE.match(line):
            sessions.append(line)
        else:
            meta.append(line)
    return meta, sessions, lines[board:]


def rotate_sessions(
    lines: list[str],
    *,
    max_keep: int,
    archive_path: Path = SESSIONS_ARCHIVE,
) -> tuple[list[str], dict[str, int]]:
    meta, sessions, board_tail = parse_session_prefix(lines)
    moved = max(0, len(sessions) - max_keep)
    kept = sessions[:max_keep]
    overflow = sessions[max_keep:]

    stats = {
        "session_total": len(sessions),
        "session_kept": len(kept),
        "session_moved": moved,
    }
    if moved == 0:
        return lines, stats

    if overflow:
        stamp = _utc_stamp()
        block = [
            f"\n## Archived {stamp} ({len(overflow)} lines)\n\n",
            *overflow,
        ]
        if archive_path.is_file():
            existing = archive_path.read_text(encoding="utf-8")
        else:
            existing = (
                "# MISSION_LOG.sessions — 세션 갱신 아카이브 (비-SSOT · 참고)\n\n"
                "> 운영 SSOT는 `MISSION_LOG.md` **작전 보드** + 상단 **최근 세션**만.\n\n"
            )
        archive_path.write_text(
            existing.rstrip("\n") + "".join(block) + "\n",
            encoding="utf-8",
        )

    archive_meta = (
        f"> **세션 아카이브:** 최근 **{max_keep}줄**만 본 파일 · 초과 → "
        f"[`MISSION_LOG.sessions.md`](MISSION_LOG.sessions.md) · "
        f"`scripts/rotate_mission_log_sessions_v1.py`\n"
    )
    new_meta: list[str] = []
    replaced = False
    for line in meta:
        if META_ARCHIVE_RE.match(line):
            new_meta.append(archive_meta)
            replaced = True
        else:
            new_meta.append(line)
    if not replaced:
        insert_at = len(new_meta)
        for i, line in enumerate(new_meta):
            if line.strip().startswith("> **재개:"):
                insert_at = i + 1
                break
        new_meta.insert(insert_at, archive_meta)

    new_lines = new_meta + kept + board_tail
    return new_lines, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-keep", type=int, default=14, help="Newest session lines to keep (default 14).")
    ap.add_argument("--mission-log", type=Path, default=LOG)
    ap.add_argument("--archive", type=Path, default=SESSIONS_ARCHIVE)
    args = ap.parse_args()

    if not args.mission_log.is_file():
        print(f"Missing: {args.mission_log}", file=sys.stderr)
        return 1
    if args.max_keep < 1:
        print("--max-keep must be >= 1", file=sys.stderr)
        return 1

    text = args.mission_log.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    new_lines, stats = rotate_sessions(lines, max_keep=args.max_keep, archive_path=args.archive)

    print(
        f"sessions total={stats['session_total']} kept={stats['session_kept']} "
        f"moved={stats['session_moved']}"
    )
    if args.dry_run:
        return 0
    if stats["session_moved"] == 0:
        return 0

    out = "".join(new_lines)
    if not out.endswith("\n"):
        out += "\n"
    args.mission_log.write_text(out, encoding="utf-8")
    print(f"WROTE: {args.mission_log}")
    if stats["session_moved"]:
        print(f"WROTE/APPEND: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
