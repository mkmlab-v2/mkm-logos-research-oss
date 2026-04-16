#!/usr/bin/env python3
"""Track C copy guard: block prohibited advisory/sales claims."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FORBIDDEN_PATTERNS = [
    r"\b(guaranteed|guarantee|guaranteed returns?)\b",
    r"\b(alpha guarantee|beat market|outperform market)\b",
    r"\b(buy now|sell now|entry point|target price)\b",
    r"\b(매수 신호|매도 신호|종목 추천|확정 수익|수익 보장)\b",
]


def _is_negated_policy_line(line: str) -> bool:
    return bool(
        re.search(
            r"\b(no|not|금지|없음|아님)\b.*\b(guarantee|보장|매수|매도|추천)\b",
            line,
            flags=re.IGNORECASE,
        )
    )


def _collect_strings(value: Any, out: list[str]) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, list):
        for v in value:
            _collect_strings(v, out)
    elif isinstance(value, dict):
        for v in value.values():
            _collect_strings(v, out)


def _extract_lines(path: Path) -> list[str]:
    if path.suffix.lower() == ".json":
        doc = json.loads(path.read_text(encoding="utf-8"))
        lines: list[str] = []
        _collect_strings(doc, lines)
        return lines
    return path.read_text(encoding="utf-8").splitlines()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Track C copy for prohibited claims.")
    parser.add_argument("path", type=Path, help="Target markdown/json/text file.")
    args = parser.parse_args()

    target = args.path.resolve()
    lines = _extract_lines(target)
    hits: list[str] = []
    for line in lines:
        if _is_negated_policy_line(line):
            continue
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line, flags=re.IGNORECASE):
                hits.append(f"{pattern} :: {line}")

    if hits:
        print(f"track_c_copy_guard: FAIL ({target})")
        for h in hits:
            print(f"- {h}")
        return 1

    print(f"track_c_copy_guard: PASS ({target})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

