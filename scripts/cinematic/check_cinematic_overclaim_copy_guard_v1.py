#!/usr/bin/env python3
"""Block cinematic overclaim phrases (Slot 2 O-01/O-02) in scenario and prompt pack."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# Slot 2 GLOBAL_TECH_CINEMATIC_SECURITY_SLOT2_V1 — O-01 agent omnipotence, O-02 Hollywood hype
FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r"\b100\s*%\s*(autonomous|자율)\b", "O-01"),
    (r"\b(완벽하게|완벽한)\s*(자율|집행|예매|결제)\b", "O-01"),
    (r"\b(hollywood|할리우드)\b", "O-02"),
    (r"\b(대형\s*영화|blockbuster)\s*(수준|급)\b", "O-02"),
    (r"\b(노트북\s*한\s*대|laptop\s*alone).{0,40}(특수\s*효과|vfx|hollywood)\b", "O-02"),
    (r"\b8k\s*hyper[- ]?realistic\b", "O-02"),
    (r"\b(전문가\s*없이|without\s*experts?).{0,30}(영화|movie|vfx)\b", "O-02"),
]


def _is_negated_policy_line(line: str) -> bool:
    return bool(
        re.search(
            r"\b(no|not|금지|없음|아님|block|reject)\b",
            line,
            flags=re.IGNORECASE,
        )
        and re.search(
            r"\b(hollywood|할리우드|자율|autonomous|완벽)\b",
            line,
            flags=re.IGNORECASE,
        )
    )


def scan_text(text: str, *, label: str) -> list[str]:
    hits: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _is_negated_policy_line(line):
            continue
        for pattern, oid in FORBIDDEN_PATTERNS:
            if re.search(pattern, line, flags=re.IGNORECASE):
                hits.append(f"{label}:{i} [{oid}] {pattern} :: {line.strip()}")
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Scenario .txt and/or prompt pack .txt to scan.",
    )
    args = parser.parse_args(argv)

    all_hits: list[str] = []
    for path in args.paths:
        target = path.resolve()
        if not target.is_file():
            print(f"cinematic_overclaim_copy_guard: missing file {target}", file=sys.stderr)
            return 1
        all_hits.extend(scan_text(target.read_text(encoding="utf-8"), label=str(target)))

    if all_hits:
        print("cinematic_overclaim_copy_guard: FAIL")
        for h in all_hits:
            print(f"- {h}")
        return 1

    print(f"cinematic_overclaim_copy_guard: PASS ({len(args.paths)} file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
