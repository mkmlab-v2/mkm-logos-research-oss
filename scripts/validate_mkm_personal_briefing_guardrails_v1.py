#!/usr/bin/env python3
"""Heuristic guardrails for MKM personal insight briefings (Fact-Lock alignment).

Blocks common rail-mixing mistakes:
- Bitcoin/A-track operational stage labels used as personal fate verdicts
- Obvious market-rail ↔ personal debt narrative bleed in the same paragraph

This does NOT prove a briefing is correct; it flags likely governance violations.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# See AGENTS.md / CENTRAL_AGENT_MEMORY: operational stages are not personal saju outputs.
OPS_STAGE_TOKENS = (
    "S0_LOCKED",
    "S1_SHADOW",
    "S2_PAPER_STRICT",
    "S3_PAPER_SCALED",
    "S4_LIMITED_LIVE",
)

_MARKET_KEYS = ("KOSPI", "BTC", "kospi", "btc", "코스피", "비트코인")
_DEBT_KEYS = ("부채", "빚", "대출", "상환")


def _read_text(path: Path | None, stdin: bool) -> str:
    if stdin:
        return sys.stdin.read()
    if path is None:
        raise ValueError("path or --stdin required")
    return path.read_text(encoding="utf-8", errors="replace")


def find_ops_stage_hits(text: str) -> list[str]:
    hits: list[str] = []
    for tok in OPS_STAGE_TOKENS:
        if tok in text:
            hits.append(tok)
    return hits


def find_market_debt_bleed(text: str) -> list[str]:
    """Same paragraph contains both market benchmark tokens and debt wording."""
    issues: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        if not para.strip():
            continue
        has_m = any(k in para for k in _MARKET_KEYS)
        has_d = any(k in para for k in _DEBT_KEYS)
        if has_m and has_d:
            issues.append("market_or_ops_benchmark_adjacent_to_personal_debt_paragraph")
            break
    return issues


def evaluate(text: str, *, strict_paragraph_bleed: bool) -> tuple[list[str], list[str]]:
    errors = [f"operational_stage_token:{t}" for t in find_ops_stage_hits(text)]
    bleed = find_market_debt_bleed(text)
    warnings: list[str] = []
    if bleed:
        if strict_paragraph_bleed:
            errors.extend(bleed)
        else:
            warnings.extend(bleed)
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate MKM personal briefing text against Fact-Lock guardrails."
    )
    ap.add_argument("path", nargs="?", type=Path, help="Markdown/text file to validate")
    ap.add_argument("--stdin", action="store_true", help="Read briefing body from stdin")
    ap.add_argument(
        "--strict-paragraph-bleed",
        action="store_true",
        help="Treat market↔debt same-paragraph bleed as error (default: warn only)",
    )
    args = ap.parse_args()

    try:
        raw = _read_text(args.path, args.stdin)
    except Exception as exc:
        print(f"read_error: {exc}", file=sys.stderr)
        return 2

    errors, warnings = evaluate(raw, strict_paragraph_bleed=args.strict_paragraph_bleed)

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    if errors:
        print("validation: failed")
        for e in errors:
            print(f"error: {e}")
        return 1

    print("validation: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
