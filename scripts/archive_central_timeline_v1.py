#!/usr/bin/env python3
"""Cap CENTRAL 「분기별 한 줄」 table; overflow → central_timeline_archive_v1.md.

Default keep newest 45 data rows.

  py scripts/archive_central_timeline_v1.py --dry-run
  py scripts/archive_central_timeline_v1.py --max-rows 45
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ROOT / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"
ARCHIVE = ROOT / "docs" / "final" / "artifacts" / "central_timeline_archive_v1.md"

SECTION_START = "## 분기별 한 줄 (최근 1년 · 수동 채움)"
SECTION_END_MARKERS = (
    "\n---\n",
    "\n## 작업 맥락 레슨",
)

ROW_RE = re.compile(r"^\|\s+20\d{2}")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_section_span(text: str) -> tuple[int, int]:
    start = text.find(SECTION_START)
    if start < 0:
        start = text.find("## 분기별 한 줄")
    if start < 0:
        raise ValueError("CENTRAL 「분기별 한 줄」 section not found")

    end = len(text)
    for marker in SECTION_END_MARKERS:
        pos = text.find(marker, start + 10)
        if pos >= 0:
            end = min(end, pos)
    return start, end


def parse_timeline_table(section: str) -> tuple[str, list[str], str]:
    """Return (preamble, data_rows, postamble within section)."""
    lines = section.splitlines(keepends=True)
    preamble: list[str] = []
    rows: list[str] = []
    post: list[str] = []
    state = "preamble"
    for line in lines:
        if state == "preamble":
            if ROW_RE.match(line):
                state = "rows"
                rows.append(line)
            else:
                preamble.append(line)
        elif state == "rows":
            if ROW_RE.match(line):
                rows.append(line)
            else:
                state = "post"
                post.append(line)
        else:
            post.append(line)
    return "".join(preamble), rows, "".join(post)


def archive_timeline_rows(
    text: str,
    *,
    max_rows: int,
    archive_path: Path = ARCHIVE,
) -> tuple[str, dict[str, int]]:
    start, end = _find_section_span(text)
    section = text[start:end]
    preamble, rows, post = parse_timeline_table(section)
    moved = max(0, len(rows) - max_rows)
    kept = rows[:max_rows]
    overflow = rows[max_rows:]

    stats = {"row_total": len(rows), "row_kept": len(kept), "row_moved": moved}
    if moved == 0:
        return text, stats

    stamp = _utc_stamp()
    archive_block = (
        f"\n## Pruned {stamp} ({len(overflow)} rows)\n\n"
        "| 기간 | 핵심 한 줄 (무엇을 확정/중단/승격했는지) |\n"
        "|------|----------------------------------------|\n"
        + "".join(overflow)
    )
    if archive_path.is_file():
        existing = archive_path.read_text(encoding="utf-8")
    else:
        existing = (
            "# CENTRAL timeline archive v1 (비-SSOT · 참고)\n\n"
            "> `docs/final/CENTRAL_AGENT_MEMORY_V1.md` 「분기별 한 줄」에서 "
            "cap 초과분만 이동. 정책·격벽 SSOT는 CENTRAL 본문·헌법.\n\n"
        )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(existing.rstrip("\n") + archive_block + "\n", encoding="utf-8")

    note = (
        f"> **타임라인 아카이브:** 본 표 **최근 {max_rows}행**만 유지 · 초과 → "
        f"`docs/final/artifacts/central_timeline_archive_v1.md` · "
        f"`scripts/archive_central_timeline_v1.py`\n\n"
    )
    if "> **타임라인 아카이브:**" in preamble:
        preamble = re.sub(
            r"> \*\*타임라인 아카이브:\*\*[^\n]*\n\n?",
            note,
            preamble,
            count=1,
        )
    else:
        preamble = preamble.replace(
            "> 팀이 실제로 한 **결정·이정표**만 적는다. 비우면 됨.\n\n",
            "> 팀이 실제로 한 **결정·이정표**만 적는다. 비우면 됨.\n\n" + note,
            1,
        )

    new_section = preamble + "".join(kept) + post
    new_text = text[:start] + new_section + text[end:]
    return new_text, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-rows", type=int, default=45, help="Newest timeline rows to keep (default 45).")
    ap.add_argument("--central", type=Path, default=CENTRAL)
    ap.add_argument("--archive", type=Path, default=ARCHIVE)
    args = ap.parse_args()

    if not args.central.is_file():
        print(f"Missing: {args.central}", file=sys.stderr)
        return 1
    if args.max_rows < 5:
        print("--max-rows must be >= 5", file=sys.stderr)
        return 1

    text = args.central.read_text(encoding="utf-8")
    new_text, stats = archive_timeline_rows(text, max_rows=args.max_rows, archive_path=args.archive)

    print(
        f"timeline rows total={stats['row_total']} kept={stats['row_kept']} "
        f"moved={stats['row_moved']}"
    )
    if args.dry_run:
        return 0
    if stats["row_moved"] == 0:
        return 0

    if not new_text.endswith("\n"):
        new_text += "\n"
    args.central.write_text(new_text, encoding="utf-8")
    print(f"WROTE: {args.central}")
    print(f"WROTE/APPEND: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
