#!/usr/bin/env python3
"""LinkedIn B2B draft copy guard — PUBLIC_FACING-aligned; no auto-publish."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFTS = ROOT / "reports/marketing/linkedin_drafts"

FORBIDDEN_PATTERNS = [
    r"\b(guaranteed|guarantee|guaranteed returns?)\b",
    r"\b100%\s*(cure|lossless|restore|success)\b",
    r"\b(regulatory risk zero|always profitable)\b",
    r"\b(neuroscience[- ]proven|hallucination eliminated)\b",
    r"\b(world[- ]unique os|beat market|target price)\b",
    r"\b(매수 신호|매도 신호|확정 수익|수익 보장)\b",
    r"신경과학적으로\s*증명",
    r"무손실\s*100%",
    r"환각\s*제거",
]

REQUIRED_MARKERS = [
    re.compile(r"\[DRAFT\]", re.I),
]


def _is_negated(line: str) -> bool:
    if re.search(
        r"\b(no|not|금지|없음|without)\b.*\b(guarantee|보장|매수|매도|수익)\b",
        line,
        flags=re.IGNORECASE,
    ):
        return True
  # KO disclaimer: "수익 보장 아님", "투자 권유 … 아님"
    if re.search(r"(보장|권유|매수|매도).{0,12}아님", line):
        return True
    if re.search(r"아님", line) and re.search(r"(보장|권유|투자)", line):
        return True
    return False


def check_file(path: Path) -> tuple[list[str], list[str]]:
    """Return (forbidden_hits, missing_required)."""
    if not path.is_file():
        return [f"file missing: {path}"], []
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    forbidden: list[str] = []
    for i, line in enumerate(lines, 1):
        if _is_negated(line):
            continue
        for pat in FORBIDDEN_PATTERNS:
            if re.search(pat, line, flags=re.IGNORECASE):
                forbidden.append(f"L{i} {pat} :: {line.strip()[:120]}")
    missing: list[str] = []
    if path.suffix.lower() == ".md":
        if not any(m.search(text) for m in REQUIRED_MARKERS):
            missing.append("[DRAFT] marker required in markdown draft")
    return forbidden, missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan LinkedIn B2B drafts for prohibited claims.")
    ap.add_argument("paths", nargs="*", type=Path, help="Files to scan (default: all *.md in drafts dir)")
    ap.add_argument("--drafts-dir", type=Path, default=DEFAULT_DRAFTS)
    args = ap.parse_args()

    if args.paths:
        targets = list(args.paths)
    else:
        targets = sorted(
            p for p in args.drafts_dir.glob("*.md") if p.name.endswith("_[DRAFT].md")
        )
    if not targets:
        print(f"linkedin_b2b_draft_copy: no targets under {args.drafts_dir}")
        return 0

    exit_code = 0
    for path in targets:
        forbidden, missing = check_file(path.resolve())
        if forbidden or missing:
            print(f"linkedin_b2b_draft_copy: FAIL ({path})")
            for h in forbidden:
                print(f"  forbidden: {h}")
            for m in missing:
                print(f"  required: {m}")
            exit_code = 1
        else:
            print(f"linkedin_b2b_draft_copy: PASS ({path})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
