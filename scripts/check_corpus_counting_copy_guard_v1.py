#!/usr/bin/env python3
"""Check copy guardrails for corpus-counting internal/external messaging."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


EXTERNAL_FORBIDDEN = [
    re.compile(r"\b(유일무이|완벽|무오류|독점적 무기|절대 표준|복제 불가)\b", re.I),
    re.compile(r"\b(no[- ]?error|perfect|unreplicable|only universal standard)\b", re.I),
    re.compile(r"41,?658.{0,40}(학계|표준|총단어|total word)", re.I),
]

INTERNAL_FORBIDDEN = [
    re.compile(r"\b(학계 표준 총단어수|only universal standard)\b", re.I),
    re.compile(r"41,?658.{0,40}(학계|표준|총단어|total word)", re.I),
]

EXTERNAL_REQUIRED_ANY = [
    "판본/카운팅 규칙",
    "separate",
    "operational",
]

INTERNAL_REQUIRED_ANY = [
    "31,102",
    "41,658",
    "운영",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _scan_patterns(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    hits: list[str] = []
    for pat in patterns:
        if pat.search(text):
            hits.append(pat.pattern)
    return hits


def _remove_forbidden_phrases_section(text: str) -> str:
    start = "## 3) Forbidden phrases"
    end = "## 4) External-safe one-paragraph copy"
    if start in text and end in text:
        i = text.index(start)
        j = text.index(end)
        return text[:i] + text[j:]
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Path relative to repo root")
    parser.add_argument(
        "--mode",
        choices=["internal", "external"],
        required=True,
        help="Validation mode",
    )
    parser.add_argument(
        "--out-json",
        default="reports/corpus_counting_copy_guard_v1_latest.json",
    )
    parser.add_argument("--stdout-only", action="store_true")
    args = parser.parse_args()

    root = _repo_root()
    target = root / args.target
    if not target.is_file():
        print(f"MISSING: {target}")
        return 2

    text = _load_text(target)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.mode == "external":
        forbidden = EXTERNAL_FORBIDDEN
        required_any = EXTERNAL_REQUIRED_ANY
        text_to_scan = _remove_forbidden_phrases_section(text)
    else:
        forbidden = INTERNAL_FORBIDDEN
        required_any = INTERNAL_REQUIRED_ANY
        text_to_scan = text

    forbidden_hits = _scan_patterns(text_to_scan, forbidden)
    required_present = any(token in text for token in required_any)

    checks = [
        {
            "id": f"{args.mode}:forbidden_patterns",
            "ok": not forbidden_hits,
            "hits": forbidden_hits,
        },
        {
            "id": f"{args.mode}:required_context_any",
            "ok": required_present,
            "required_any": required_any,
        },
    ]

    passed = all(bool(item["ok"]) for item in checks)
    report = {
        "schema": "corpus_counting_copy_guard_v1",
        "generated_at_utc": generated_at,
        "mode": args.mode,
        "target": args.target,
        "passed": passed,
        "checks": checks,
    }

    out_path = root / args.out_json
    if not args.stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.stdout_only:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"WROTE: {out_path}")
        print(f"passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

