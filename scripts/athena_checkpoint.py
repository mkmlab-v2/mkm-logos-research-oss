#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append a one-line operational checkpoint in CENTRAL_AGENT_MEMORY_V1.md.

Updates ``last_updated_utc`` in the ## 메타 block and **prepends** a new bullet
between ``<!-- ATHENA_CHECKPOINT_V1_START -->`` and ``<!-- ATHENA_CHECKPOINT_V1_END -->``,
keeping prior checkpoint lines up to ``--max-checkpoints`` (oldest dropped when over).

On first run, inserts that section after the meta bullets (before the first ``---``).

This is a **low-risk file edit**: run directly::

  py scripts/athena_checkpoint.py "done: X, next: Y"

Do **not** wrap with ``athena_run_v1.py`` unless you intentionally want ECC audit on the
child — checkpoint does not touch secrets or live trade paths.

Usage:
  py scripts/athena_checkpoint.py "message"
  py scripts/athena_checkpoint.py --dry-run "message"
  py scripts/athena_checkpoint.py --path docs/final/CENTRAL_AGENT_MEMORY_V1.md "message"
  py scripts/athena_checkpoint.py --replace-all "only this line remains"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CENTRAL = WORKSPACE_ROOT / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"

MARK_START = "<!-- ATHENA_CHECKPOINT_V1_START -->"
MARK_END = "<!-- ATHENA_CHECKPOINT_V1_END -->"
# Ops memory index gate: prism_ops_central_checkpoint must_keep_tags includes "CENTRAL".
CENTRAL_MARKER = "<!-- CENTRAL checkpoint block -->"

SECTION_HEADER = "## 운영 체크포인트 (자동, 1줄)"

DEFAULT_MAX_CHECKPOINTS = 20


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


def _checkpoint_body_single(stamp: str, message: str) -> str:
    line = f"- **{stamp}** — {message.strip()}"
    return f"{MARK_START}\n{CENTRAL_MARKER}\n{line}\n{MARK_END}"


def _checkpoint_bullets_from_inner(inner: str) -> list[str]:
    bullets: list[str] = []
    for line in inner.splitlines():
        stripped = line.strip()
        if stripped.startswith("- **"):
            bullets.append(line.rstrip())
    return bullets


def _merge_checkpoint_inner(
    inner_between_markers: str,
    stamp: str,
    message: str,
    max_lines: int,
) -> str:
    """Build inner body (no MARK_* lines): marker comment, new bullet first, then prior bullets."""
    new_line = f"- **{stamp}** — {message.strip()}"
    prev = _checkpoint_bullets_from_inner(inner_between_markers)
    merged = [new_line] + prev
    if len(merged) > max_lines:
        merged = merged[:max_lines]
    return "\n".join([CENTRAL_MARKER, *merged])


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
            + _checkpoint_body_single(stamp, message)
            + m.group(2)
        )

    new_content, n = re.subn(pattern, _repl, content, count=1, flags=re.DOTALL)
    if n == 1:
        return new_content
    raise RuntimeError(
        "Could not find insertion anchor (external_briefing_ref_v2 + --- + NotebookLM heading). "
        "Add markers manually or fix CENTRAL_AGENT_MEMORY_V1.md structure."
    )


def _replace_checkpoint(
    content: str,
    stamp: str,
    message: str,
    *,
    replace_all: bool,
    max_checkpoints: int,
) -> str:
    if MARK_START not in content or MARK_END not in content:
        return _insert_section_if_missing(content, stamp, message)

    m = re.search(re.escape(MARK_START) + r"([\s\S]*?)" + re.escape(MARK_END), content)
    if not m:
        return _insert_section_if_missing(content, stamp, message)

    inner = m.group(1)
    if replace_all:
        inner_body = f"- **{stamp}** — {message.strip()}"
    else:
        inner_body = _merge_checkpoint_inner(inner, stamp, message, max_checkpoints)
    replacement = f"{MARK_START}\n{inner_body}\n{MARK_END}"
    return content[: m.start()] + replacement + content[m.end() :]


APPEND_TURN_META = Path(__file__).resolve().parent / "append_mkm_cursor_turn_meta_v1.py"


def _append_turn_meta_after_checkpoint(
    *,
    lane: str,
    continuity_id: str,
    checkpoint_message: str,
    dry_run: bool,
) -> int:
    if dry_run:
        print(
            f"Would append turn_meta lane={lane} continuity_id={continuity_id} "
            f"message={checkpoint_message!r}"
        )
        return 0
    proc = subprocess.run(
        [
            sys.executable,
            str(APPEND_TURN_META),
            "--lane",
            lane,
            "--continuity-id",
            continuity_id,
            "--checkpoint-message",
            checkpoint_message,
        ],
        cwd=WORKSPACE_ROOT,
        check=False,
    )
    if proc.returncode != 0:
        print(f"WARN: append_mkm_cursor_turn_meta exit {proc.returncode}", file=sys.stderr)
        return int(proc.returncode)
    print(f"OK: turn_meta appended continuity_id={continuity_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Update CENTRAL checkpoint (prepend) + last_updated_utc.")
    p.add_argument(
        "message",
        nargs="?",
        default="",
        help="One-line checkpoint message (quote on shells).",
    )
    p.add_argument("--path", type=Path, default=DEFAULT_CENTRAL, help="Path to CENTRAL_AGENT_MEMORY_V1.md")
    p.add_argument("--dry-run", action="store_true", help="Print actions; do not write")
    p.add_argument(
        "--replace-all",
        action="store_true",
        help="Replace entire checkpoint block with a single line (legacy behavior).",
    )
    p.add_argument(
        "--max-checkpoints",
        type=int,
        default=DEFAULT_MAX_CHECKPOINTS,
        metavar="N",
        help=f"Max bullet lines to keep after prepend (default {DEFAULT_MAX_CHECKPOINTS}).",
    )
    p.add_argument(
        "--continuity-id",
        default="",
        help="Optional continuity id prefix for multi-chat tasks (prepended to message).",
    )
    p.add_argument(
        "--lane",
        default="infra",
        help="Lane for turn_meta append when --continuity-id is set (default infra).",
    )
    p.add_argument(
        "--skip-turn-meta",
        action="store_true",
        help="Skip append_mkm_cursor_turn_meta_v1 even when --continuity-id is set.",
    )
    args = p.parse_args(argv)

    raw_msg = (args.message or "").strip()
    if not raw_msg:
        print("error: message required, e.g. py scripts/athena_checkpoint.py \"done: X\"", file=sys.stderr)
        return 1

    msg = raw_msg
    if args.continuity_id.strip():
        msg = f"continuity={args.continuity_id.strip()} · {raw_msg}"

    path: Path = args.path
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    if args.max_checkpoints < 1:
        print("error: --max-checkpoints must be >= 1", file=sys.stderr)
        return 1

    stamp = _utc_now_z()
    raw = path.read_text(encoding="utf-8")
    updated = _replace_last_updated(raw, stamp)
    updated = _replace_checkpoint(
        updated,
        stamp,
        msg,
        replace_all=args.replace_all,
        max_checkpoints=args.max_checkpoints,
    )

    if args.dry_run:
        print(f"Would write: {path}")
        print(f"last_updated_utc: {stamp}")
        m = re.search(re.escape(MARK_START) + r"[\s\S]*?" + re.escape(MARK_END), updated)
        print("checkpoint block:")
        print(m.group(0) if m else "(marker block not found — check anchor)")
        if args.continuity_id.strip() and not args.skip_turn_meta:
            _append_turn_meta_after_checkpoint(
                lane=args.lane.strip() or "infra",
                continuity_id=args.continuity_id.strip(),
                checkpoint_message=raw_msg,
                dry_run=True,
            )
        return 0

    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"OK: {path}")
    print(f"last_updated_utc: {stamp}")
    print(f"checkpoint: {msg}")

    if args.continuity_id.strip() and not args.skip_turn_meta:
        return _append_turn_meta_after_checkpoint(
            lane=args.lane.strip() or "infra",
            continuity_id=args.continuity_id.strip(),
            checkpoint_message=raw_msg,
            dry_run=False,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
