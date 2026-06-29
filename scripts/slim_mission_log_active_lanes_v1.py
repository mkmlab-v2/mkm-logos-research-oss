#!/usr/bin/env python3
"""Keep MISSION_LOG slim: header + lane table + active ### sections only; archive the rest.

  py scripts/slim_mission_log_active_lanes_v1.py --dry-run
  py scripts/slim_mission_log_active_lanes_v1.py
"""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "MISSION_LOG.md"
OLD = ROOT / "MISSION_LOG.old.md"
BACKUP = ROOT / "MISSION_LOG.pre_slim_lanes_backup.md"

BOARD_START = "## 🚀 전술 작전 보드"

# Active lane blocks kept in SSOT (prefix match on ### title line).
ACTIVE_SECTION_PREFIXES = (
    "### 💼 MS ·",
    "### 🧭 Cursor IDE ·",
    "### 🔮 Oracle ·",
    "### 🖥️ Infra · 스케줄러 solo stack",
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _split_h3_sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []
    for line in lines:
        if line.startswith("### "):
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = line.rstrip("\n")
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))
    return sections


def _is_active(title: str) -> bool:
    return any(title.startswith(p) for p in ACTIVE_SECTION_PREFIXES)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not LOG.is_file():
        raise SystemExit(f"Missing: {LOG}")

    text = LOG.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    board_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(BOARD_START):
            board_idx = i
            break
    if board_idx < 0:
        raise SystemExit(f"Missing board marker: {BOARD_START!r}")

    prefix = lines[:board_idx]
    board_and_rest = lines[board_idx:]
    # First line is board header; rest may include pre-section content (rare).
    pre_section: list[str] = []
    section_lines: list[str] = []
    seen_h3 = False
    for line in board_and_rest[1:]:
        if line.startswith("### "):
            seen_h3 = True
            section_lines.append(line)
        elif seen_h3:
            section_lines.append(line)
        else:
            pre_section.append(line)

    sections = _split_h3_sections(section_lines)
    active: list[str] = []
    archived: list[str] = []
    for title, body in sections:
        if _is_active(title):
            active.extend(body)
        else:
            archived.extend(body)

    archive_note = (
        f"\n> **아카이브:** closed·과거 작전 블록 → [`MISSION_LOG.old.md`](MISSION_LOG.old.md) "
        f"(slim `{_utc_stamp()}`)\n\n"
    )
    new_log_parts = (
        prefix
        + [lines[board_idx]]
        + pre_section
        + [archive_note]
        + active
    )
    new_log = "".join(new_log_parts)
    if not new_log.endswith("\n"):
        new_log += "\n"

    archive_block = (
        f"\n---\n\n## MISSION_LOG ARCHIVE — slim active-lanes (`{_utc_stamp()}`)\n\n"
        f"출처: `scripts/slim_mission_log_active_lanes_v1.py` · "
        f"제거된 ### 블록 **{len(sections) - sum(1 for t, _ in sections if _is_active(t))}**개\n\n"
    )
    old_parts: list[str] = []
    if OLD.is_file():
        old_parts.append(OLD.read_text(encoding="utf-8").rstrip() + "\n")
    old_parts.append(archive_block)
    old_parts.extend(archived)
    new_old = "".join(old_parts)
    if not new_old.endswith("\n"):
        new_old += "\n"

    kept = sum(1 for t, _ in sections if _is_active(t))
    print(
        f"sections_total={len(sections)} kept={kept} archived={len(sections) - kept} "
        f"new_log_lines≈{len(new_log.splitlines())} archive_add_lines≈{len(archived)}"
    )

    if args.dry_run:
        return 0

    shutil.copy2(LOG, BACKUP)
    LOG.write_text(new_log, encoding="utf-8")
    OLD.write_text(new_old, encoding="utf-8")
    print(f"backup: {BACKUP}")
    print(f"WROTE: {LOG}")
    print(f"WROTE: {OLD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
