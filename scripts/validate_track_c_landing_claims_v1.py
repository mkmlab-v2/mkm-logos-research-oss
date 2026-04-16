#!/usr/bin/env python3
"""Validate Track C landing claims against evidence and disclaimer policy."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


FORBIDDEN_PATTERNS = [
    r"\b(guaranteed|guarantee)\b",
    r"\b(alpha|beat market|outperform)\b",
    r"\b(buy now|sell now|entry point|target price)\b",
    r"\b(확정 수익|수익 보장|매수 신호|매도 신호|종목 추천)\b",
]

REQUIRED_PHRASES = [
    "not investment advice",
    "risk warning",
]


def _is_negated_policy_line(line: str) -> bool:
    return bool(
        re.search(
            r"\b(no|not|금지|없음|아님)\b.*\b(guarantee|보장|매수|매도|추천)\b",
            line,
            flags=re.IGNORECASE,
        )
    )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return obj


def _collect_strings(value: Any, out: list[str]) -> None:
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, list):
        for v in value:
            _collect_strings(v, out)
    elif isinstance(value, dict):
        for v in value.values():
            _collect_strings(v, out)


def validate_claims(lines: list[str], required_disclaimer: str) -> list[str]:
    errors: list[str] = []
    flattened_lines: list[str] = []
    for line in lines:
        flattened_lines.extend(str(line).splitlines())
    filtered_lines = [line for line in flattened_lines if not _is_negated_policy_line(line)]
    joined = "\n".join(filtered_lines).lower()

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, joined, flags=re.IGNORECASE):
            errors.append(f"forbidden claim pattern matched: {pattern}")

    for phrase in REQUIRED_PHRASES:
        if phrase not in joined:
            errors.append(f"missing required phrase: {phrase}")

    if required_disclaimer.lower() not in joined:
        errors.append("missing required_disclaimer from evidence pack")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Track C landing claim safety.")
    repo_root_default = Path(__file__).resolve().parents[1]
    parser.add_argument("--repo-root", type=Path, default=repo_root_default)
    parser.add_argument(
        "--landing-copy",
        type=Path,
        default=Path("docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md"),
    )
    parser.add_argument(
        "--evidence-pack",
        type=Path,
        default=Path("docs/final/artifacts/track_c_evidence_pack_latest.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    landing_path = args.landing_copy if args.landing_copy.is_absolute() else (repo_root / args.landing_copy)
    evidence_path = args.evidence_pack if args.evidence_pack.is_absolute() else (repo_root / args.evidence_pack)

    if landing_path.suffix.lower() == ".json":
        landing_doc = _load_json(landing_path)
        lines: list[str] = []
        _collect_strings(landing_doc, lines)
    else:
        lines = [landing_path.read_text(encoding="utf-8")]
    evidence_doc = _load_json(evidence_path)
    required_disclaimer = str((evidence_doc.get("commercial_scope") or {}).get("required_disclaimer") or "").strip()
    if not required_disclaimer:
        raise SystemExit("evidence pack missing commercial_scope.required_disclaimer")

    errors = validate_claims(lines, required_disclaimer=required_disclaimer)
    if errors:
        print("track_c_landing_claims: FAIL")
        for e in errors:
            print(f"- {e}")
        return 1

    print("track_c_landing_claims: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

