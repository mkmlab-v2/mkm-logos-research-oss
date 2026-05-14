#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append bullets under a ## Thread N section in the daily multi-chat work log.

Default file: ``reports/daily_thread_work_{local-date}.md`` (under workspace root).
Override with env ``MKM_DAILY_THREAD_LOG_PATH`` (full path to ``.md``, or a directory —
then ``{name}/daily_thread_work_{date}.md`` is used when path is dir).

If the log file is missing, it is created from ``docs/final/templates/DAILY_THREAD_WORK_LOG.template.md``.

Examples::

  py scripts/athena_daily_thread_log_sync_v1.py --thread 2 --bullet "done: X" --bullet "next: Y"
  py scripts/athena_daily_thread_log_sync_v1.py --date 2026-05-14 --thread 1 --bullet "smoke OK"
  py scripts/athena_daily_thread_log_sync_v1.py --print-path
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import List, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = WORKSPACE_ROOT / "docs" / "final" / "templates" / "DAILY_THREAD_WORK_LOG.template.md"


def _workspace_root() -> Path:
    raw = (os.environ.get("MKM_WORKSPACE_ROOT") or "").strip()
    return Path(raw).resolve() if raw else WORKSPACE_ROOT


def _resolve_log_path(root: Path, day: date) -> Path:
    raw = (os.environ.get("MKM_DAILY_THREAD_LOG_PATH") or "").strip()
    name = f"daily_thread_work_{day.isoformat()}.md"
    if not raw:
        return root / "reports" / name
    p = Path(os.path.expandvars(raw)).expanduser()
    if not p.is_absolute():
        p = (root / p).resolve()
    if p.is_dir():
        return (p / name).resolve()
    return p.resolve()


def _normalize_bullets(items: List[str]) -> List[str]:
    out: List[str] = []
    for s in items:
        t = (s or "").strip()
        if not t:
            continue
        if t.startswith(("- ", "* ")):
            t = t[2:].strip()
        out.append(t)
    return out


def _section_insert_index(lines: List[str], thread: int) -> Tuple[int | None, int]:
    """Return (header_line_index or None if missing, insert_before_line_index).

    If the ``## Thread N`` header exists, bullets are inserted immediately before
    the next line that starts with ``## `` (exclusive end of section body).
    """
    head = re.compile(rf"^##\s+Thread\s+{int(thread)}\b", re.I)
    for i, line in enumerate(lines):
        if head.match(line):
            start = i + 1
            end = len(lines)
            for j in range(start, len(lines)):
                if lines[j].startswith("## "):
                    end = j
                    break
            return i, end
    return None, len(lines)


def merge_bullets_into_content(content: str, thread: int, bullets: List[str]) -> str:
    """Return updated markdown: append normalized bullets under ``## Thread {thread}``."""
    bs = _normalize_bullets(bullets)
    if not bs:
        return content
    if not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines(keepends=True)
    hi, ins = _section_insert_index(lines, thread)
    ins_lines = [f"- {b}\n" for b in bs]
    if hi is None:
        lines.append(f"\n## Thread {int(thread)} — (topic)\n")
        lines.extend(ins_lines)
    else:
        lines[ins:ins] = ins_lines
    return "".join(lines)


def _materialize_from_template(dest: Path, day: date) -> None:
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"Template missing: {TEMPLATE}")
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("{{DATE}}", day.isoformat())
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--thread", type=int, default=None, help="Thread number 1..10 (omit with --print-path)")
    ap.add_argument(
        "--bullet",
        action="append",
        default=[],
        metavar="TEXT",
        help="Bullet body (repeatable). Leading '- ' is stripped.",
    )
    ap.add_argument("--date", default="", help="ISO date YYYY-MM-DD (default: local today)")
    ap.add_argument(
        "--print-path",
        action="store_true",
        help="Print resolved log path and exit 0 (no write)",
    )
    args = ap.parse_args()

    root = _workspace_root()
    if args.date.strip():
        day = date.fromisoformat(args.date.strip())
    else:
        day = date.today()
    path = _resolve_log_path(root, day)

    if args.print_path:
        print(str(path))
        return 0

    if args.thread is None:
        print("--thread is required unless using --print-path", file=sys.stderr)
        return 2

    if not (1 <= int(args.thread) <= 10):
        print("--thread must be 1..10", file=sys.stderr)
        return 2

    bs = _normalize_bullets(list(args.bullet or []))
    if not bs:
        print("Provide at least one --bullet", file=sys.stderr)
        return 2

    if not path.is_file():
        _materialize_from_template(path, day)

    body = path.read_text(encoding="utf-8")
    new_body = merge_bullets_into_content(body, int(args.thread), bs)
    path.write_text(new_body, encoding="utf-8", newline="\n")
    print(f"Updated {path} (thread {int(args.thread)}, {len(bs)} bullet(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
