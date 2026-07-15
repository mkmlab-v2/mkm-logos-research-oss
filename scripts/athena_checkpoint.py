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
  py scripts/athena_checkpoint.py --origin external_paste "pasted note"
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
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))
from athena_checkpoint_provenance_v1 import (  # noqa: E402
    append_provenance_jsonl,
    build_provenance_row,
    normalize_provenance,
)

MARK_START = "<!-- ATHENA_CHECKPOINT_V1_START -->"
MARK_END = "<!-- ATHENA_CHECKPOINT_V1_END -->"
# Ops memory index gate: prism_ops_central_checkpoint must_keep_tags includes "CENTRAL".
CENTRAL_MARKER = "<!-- CENTRAL checkpoint block -->"

SECTION_HEADER = "## 운영 체크포인트 (자동, 1줄)"

DEFAULT_MAX_CHECKPOINTS = 20
# Same continuity_id within this window replaces the newest bullet (burst dedupe).
DEFAULT_SAME_CONTINUITY_BURST_SECONDS = 60

CONTINUITY_PREFIX_RE = re.compile(
    r"^continuity=([a-z0-9][a-z0-9._-]{2,127})\s*·\s*",
    re.I,
)


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_checkpoint_bullet(line: str) -> tuple[str, str, str] | None:
    """Return (stamp_utc, continuity_id, message_body) or None."""
    m = re.match(
        r"^-\s+\*\*(\d{4}-\d{2}-\d{2}T[\d:.]+Z)\*\*\s+—\s+(.+)$",
        line.strip(),
    )
    if not m:
        return None
    stamp, message = m.group(1), m.group(2).strip()
    cont = ""
    cm = CONTINUITY_PREFIX_RE.match(message)
    if cm:
        cont = cm.group(1)
    return stamp, cont, message


def _parse_iso_utc(stamp: str) -> datetime:
    s = stamp.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


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
    *,
    same_continuity_burst_seconds: int = DEFAULT_SAME_CONTINUITY_BURST_SECONDS,
) -> str:
    """Build inner body (no MARK_* lines): marker comment, new bullet first, then prior bullets.

    When the newest prior bullet shares continuity_id with the incoming message and the
    stamps are within ``same_continuity_burst_seconds``, replace that bullet instead of
    prepending (burst dedupe).
    """
    new_line = f"- **{stamp}** — {message.strip()}"
    prev = _checkpoint_bullets_from_inner(inner_between_markers)

    incoming = _parse_checkpoint_bullet(new_line)
    if incoming and prev and same_continuity_burst_seconds > 0:
        new_stamp, new_cont, _ = incoming
        if new_cont:
            try:
                new_dt = _parse_iso_utc(new_stamp)
            except ValueError:
                new_dt = None
            if new_dt is not None:
                for idx, bullet in enumerate(prev):
                    parsed = _parse_checkpoint_bullet(bullet)
                    if not parsed:
                        continue
                    prev_stamp, prev_cont, _ = parsed
                    if prev_cont != new_cont:
                        continue
                    try:
                        prev_dt = _parse_iso_utc(prev_stamp)
                    except ValueError:
                        continue
                    delta = abs((new_dt - prev_dt).total_seconds())
                    if delta <= float(same_continuity_burst_seconds):
                        prev = prev[:idx] + prev[idx + 1 :]
                        break

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
    same_continuity_burst_seconds: int = DEFAULT_SAME_CONTINUITY_BURST_SECONDS,
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
        inner_body = _merge_checkpoint_inner(
            inner,
            stamp,
            message,
            max_checkpoints,
            same_continuity_burst_seconds=same_continuity_burst_seconds,
        )
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
        "--same-continuity-burst-seconds",
        type=int,
        default=DEFAULT_SAME_CONTINUITY_BURST_SECONDS,
        metavar="SEC",
        help=(
            "Within SEC seconds, a new checkpoint with the same continuity= id "
            f"replaces the newest prior bullet instead of prepending (default {DEFAULT_SAME_CONTINUITY_BURST_SECONDS})."
        ),
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
    p.add_argument(
        "--origin",
        default="commander",
        choices=["commander", "agent_summary", "tool", "external_paste"],
        help="Write-path origin for provenance sidecar (default commander).",
    )
    p.add_argument(
        "--trust",
        default="",
        choices=["", "high", "medium", "low", "unknown"],
        help="Trust label (default by origin).",
    )
    p.add_argument(
        "--allow-act",
        dest="allow_act",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Consequential-act elevation (default: true only for commander; forced false for external_paste).",
    )
    p.add_argument(
        "--skip-provenance",
        action="store_true",
        help="Skip provenance JSONL sidecar (not recommended).",
    )
    args = p.parse_args(argv)

    raw_msg = (args.message or "").strip()
    if not raw_msg:
        print("error: message required, e.g. py scripts/athena_checkpoint.py \"done: X\"", file=sys.stderr)
        return 1

    try:
        prov = normalize_provenance(
            origin=args.origin,
            trust=args.trust or None,
            allow_act=args.allow_act,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
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
        same_continuity_burst_seconds=args.same_continuity_burst_seconds,
    )

    try:
        relative_central = str(path.resolve().relative_to(WORKSPACE_ROOT.resolve()))
    except ValueError:
        relative_central = str(path)

    prov_row = build_provenance_row(
        stamp_utc=stamp,
        message=raw_msg,
        message_written=msg,
        origin=prov["origin"],
        trust=prov["trust"],
        allow_act=prov["allow_act"],
        continuity_id=args.continuity_id.strip(),
        lane=(args.lane.strip() or "infra"),
        central_path=relative_central,
    )

    if args.dry_run:
        print(f"Would write: {path}")
        print(f"last_updated_utc: {stamp}")
        m = re.search(re.escape(MARK_START) + r"[\s\S]*?" + re.escape(MARK_END), updated)
        print("checkpoint block:")
        print(m.group(0) if m else "(marker block not found — check anchor)")
        print(
            f"provenance: origin={prov['origin']} trust={prov['trust']} "
            f"allow_act={prov['allow_act']}"
        )
        if not args.skip_provenance:
            append_provenance_jsonl(prov_row, dry_run=True)
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
    print(
        f"provenance: origin={prov['origin']} trust={prov['trust']} "
        f"allow_act={prov['allow_act']}"
    )

    if not args.skip_provenance:
        try:
            append_provenance_jsonl(prov_row, dry_run=False)
            print("OK: provenance sidecar reports/athena_checkpoint_provenance_v1.jsonl")
        except ValueError as exc:
            print(f"FAIL: provenance {exc}", file=sys.stderr)
            return 1

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
