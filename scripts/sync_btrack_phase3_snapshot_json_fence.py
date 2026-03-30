#!/usr/bin/env python3
"""Replace the first ```json ... ``` fence in btrack_phase3_cross_ref_snapshot.md with SSOT JSON.

SSOT file: docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json (v2 draft).
Does not rewrite the plain-text ENTRY_* block below the fence. After edits to SSOT, run:

  py scripts/sync_btrack_phase3_snapshot_json_fence.py --apply

Then: py -m pytest tests/test_cross_ref_dss_schema.py -q
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def find_json_fence_slice(lines: list[str]) -> tuple[int, int] | None:
    """Return (start_line_idx_inclusive, end_line_idx_exclusive) for content between fences."""
    open_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == "```json":
            open_idx = i
            continue
        if open_idx is not None and line.strip() == "```":
            return (open_idx + 1, i)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync btrack Phase3 snapshot JSON fence from CROSS_REF SSOT")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write snapshot file (default: dry-run)",
    )
    ap.add_argument(
        "--ssot",
        type=Path,
        default=None,
        help="CROSS_REF JSON path (default: docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json)",
    )
    ap.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="btrack snapshot MD (default: docs/final/btrack_phase3_cross_ref_snapshot.md)",
    )
    args = ap.parse_args()
    root = repo_root()
    ssot = args.ssot or (root / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json")
    snap = args.snapshot or (root / "docs/final/btrack_phase3_cross_ref_snapshot.md")
    if not ssot.is_file():
        print(f"ERROR: SSOT missing: {ssot}", file=sys.stderr)
        return 2
    if not snap.is_file():
        print(f"ERROR: snapshot missing: {snap}", file=sys.stderr)
        return 2

    doc = json.loads(ssot.read_text(encoding="utf-8"))
    new_json = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    text = snap.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    slc = find_json_fence_slice(lines)
    if slc is None:
        print("ERROR: no ```json ... ``` fence found in snapshot", file=sys.stderr)
        return 2
    a, b = slc
    old_block = "".join(lines[a:b])
    if old_block == new_json:
        print("OK: fence already matches SSOT (no write needed)")
        return 0

    print(f"INFO: replacing fence lines {a + 1}-{b} ({b - a} lines) with SSOT ({len(new_json.splitlines())} lines)")
    if not args.apply:
        print("DRY-RUN: pass --apply to write")
        return 0

    out = lines[:a] + [new_json] + lines[b:]
    snap.write_text("".join(out), encoding="utf-8")
    print(f"WROTE: {snap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
