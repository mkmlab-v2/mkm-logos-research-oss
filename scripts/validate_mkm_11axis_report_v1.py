#!/usr/bin/env python3
"""Validate MKM 11-axis report evidence tags.

Rules:
- Axis sections 1..11 must each contain at least one evidence tag:
  [FACT] / [ESTIMATE] / [HYPO]
- If axis 7 or 9 contains an explicit fail marker with FACT
  (e.g. "[FACT] ... FAIL"), final action must be HOLD.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

EVIDENCE_RE = re.compile(r"\[(FACT|ESTIMATE|HYPO)\]")
AXIS_TITLE_RE = re.compile(r"^##\s+Axis\s+(\d+)\b", re.IGNORECASE)
FINAL_ACTION_RE = re.compile(r"^\-\s*action:\s*(\w+)\s*$", re.IGNORECASE)


def _slice_axis_sections(lines: list[str]) -> dict[int, list[str]]:
    sections: dict[int, list[str]] = {}
    starts: list[tuple[int, int]] = []
    for idx, line in enumerate(lines):
        m = AXIS_TITLE_RE.match(line.strip())
        if m:
            starts.append((int(m.group(1)), idx))
    for i, (axis, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(lines)
        sections[axis] = lines[start:end]
    return sections


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report_path", type=Path, help="Path to markdown report")
    args = ap.parse_args()

    if not args.report_path.is_file():
        print(f"missing report: {args.report_path}")
        return 2

    lines = args.report_path.read_text(encoding="utf-8").splitlines()
    sections = _slice_axis_sections(lines)

    missing_axes = [axis for axis in range(1, 12) if axis not in sections]
    if missing_axes:
        print(f"missing axis sections: {missing_axes}")
        return 3

    no_evidence_axes: list[int] = []
    fact_fail_7_or_9 = False
    for axis in range(1, 12):
        body = "\n".join(sections[axis])
        if not EVIDENCE_RE.search(body):
            no_evidence_axes.append(axis)
        if axis in (7, 9):
            # conservative pattern: FACT + FAIL on the same axis block
            if "[FACT]" in body.upper() and "FAIL" in body.upper():
                fact_fail_7_or_9 = True

    if no_evidence_axes:
        print(f"axes missing evidence tier tag: {no_evidence_axes}")
        return 4

    final_action = ""
    for line in lines:
        m = FINAL_ACTION_RE.match(line.strip())
        if m:
            final_action = m.group(1).upper()
            break

    if not final_action:
        print("missing final action line: '- action: ...'")
        return 5

    if fact_fail_7_or_9 and final_action != "HOLD":
        print("policy violation: axis7/9 FACT fail requires action HOLD")
        return 6

    print("ok mkm_11axis_report_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
