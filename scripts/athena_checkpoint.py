#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append/replace a one-line operational checkpoint in CENTRAL_AGENT_MEMORY_V1.md.

Updates ``last_updated_utc`` in the ## 메타 block and maintains a delimited one-liner
between ``<!-- ATHENA_CHECKPOINT_V1_START -->`` and ``<!-- ATHENA_CHECKPOINT_V1_END -->``.
On first run, inserts that section after the meta bullets (before the first ``---``).

This is a **low-risk file edit**: run directly::

  py scripts/athena_checkpoint.py "done: X, next: Y"

Do **not** wrap with ``athena_run_v1.py`` unless you intentionally want ECC audit on the
child — checkpoint does not touch secrets or live trade paths.

Usage:
  py scripts/athena_checkpoint.py "message"
  py scripts/athena_checkpoint.py --dry-run "message"
  py scripts/athena_checkpoint.py --path docs/final/CENTRAL_AGENT_MEMORY_V1.md "message"
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENTRAL = WORKSPACE_ROOT / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"

MARK_START = "<!-- ATHENA_CHECKPOINT_V1_START -->"
MARK_END = "<!-- ATHENA_CHECKPOINT_V1_END -->"

SECTION_HEADER = "## 운영 체크포인트 (자동, 1줄)"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _replace_last_updated(content: str, stamp: str) -> str:
    # Line is: - **last_updated_utc:** 2026-...Z
    return re.sub(
        r"^(- \*\*last_updated_utc:\*\*)\s+\S+",
        rf"\1 {stamp}",
        content,
        count=1,
        flags=re.MULTILINE,
    )


def _checkpoint_body(stamp: str, message: str) -> str:
    line = f"- **{stamp}** — {message.strip()}"
    return f"{MARK_START}\n{line}\n{MARK_END}"


def _insert_section_if_missing(content: str, stamp: str, message: str) -> str:
    if MARK_START in content and MARK_END in content:
        return content
    # Insert after last meta bullet (external_briefing_ref_v2) and before the first --- divider.
    pattern = (
        r"(- \*\*external_briefing_ref_v2:\*\*[^\n]*\n)"
        r"(\n---\n\n## NotebookLM → 장기기억 체화 \(한 파일 SSOT\))"
    )

    def _repl(m: re.Match[str]) -> str:
        return (
            m.group(1)
            + "\n"
            + SECTION_HEADER
            + "\n\n"
            + _checkpoint_body(stamp, message)
            + m.group(2)
        )

    new_content, n = re.subn(pattern, _repl, content, count=1, flags=re.DOTALL)
    if n == 1:
        return new_content
    raise RuntimeError(
        "Could not find insertion anchor (external_briefing_ref_v2 + --- + NotebookLM heading). "
        "Add markers manually or fix CENTRAL_AGENT_MEMORY_V1.md structure."
    )


def _replace_checkpoint(content: str, stamp: str, message: str) -> str:
    inner = _checkpoint_body(stamp, message)
    if MARK_START in content and MARK_END in content:
        return re.sub(
            re.escape(MARK_START) + r"[\s\S]*?" + re.escape(MARK_END),
            inner,
            content,
            count=1,
        )
    return _insert_section_if_missing(content, stamp, message)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Update CENTRAL one-line checkpoint + last_updated_utc.")
    p.add_argument(
        "message",
        nargs="?",
        default="",
        help="One-line checkpoint message (quote on shells).",
    )
    p.add_argument("--path", type=Path, default=DEFAULT_CENTRAL, help="Path to CENTRAL_AGENT_MEMORY_V1.md")
    p.add_argument("--dry-run", action="store_true", help="Print actions; do not write")
    args = p.parse_args(argv)

    msg = (args.message or "").strip()
    if not msg:
        print("error: message required, e.g. py scripts/athena_checkpoint.py \"done: X\"", file=sys.stderr)
        return 1

    path: Path = args.path
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    stamp = _utc_now_z()
    raw = path.read_text(encoding="utf-8")
    updated = _replace_last_updated(raw, stamp)
    updated = _replace_checkpoint(updated, stamp, msg)

    if args.dry_run:
        print(f"Would write: {path}")
        print(f"last_updated_utc: {stamp}")
        m = re.search(re.escape(MARK_START) + r"[\s\S]*?" + re.escape(MARK_END), updated)
        print("checkpoint block:")
        print(m.group(0) if m else "(marker block not found — check anchor)")
        return 0

    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"OK: {path}")
    print(f"last_updated_utc: {stamp}")
    print(f"checkpoint: {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
