#!/usr/bin/env python3
"""PUBLIC_FACING gate for 광명백제 당근 동네생활 copy pack [HYPO]."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "final" / "artifacts" / "gwangmyeong_baekje_daangn_copy_contract_v1_latest.json"


def load_contract(path: Path = CONTRACT) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "gwangmyeong_baekje_daangn_copy_contract_v1":
        raise ValueError(f"unexpected_contract_schema: {doc.get('schema')}")
    return doc


def _line_excluded(line: str, negation_markers: tuple[str, ...]) -> bool:
    return any(m in line for m in negation_markers)


def check_files(contract: dict, *, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    forbidden = list(contract.get("forbidden_substrings") or [])
    forbidden_re = [re.compile(p, re.I) for p in (contract.get("forbidden_regex") or [])]
    negation = tuple(contract.get("negation_markers") or ())
    required_framing = list(contract.get("required_framing") or [])
    required_any_post = list(contract.get("required_substrings_any_post") or [])

    post_bodies = [
        "reports/gwangmyeong_baekje_daangn_paste/post_a_chuna_body.txt",
        "reports/gwangmyeong_baekje_daangn_paste/post_b_traffic_body.txt",
        "reports/gwangmyeong_baekje_daangn_paste/post_c_core_body.txt",
    ]

    for rel in contract.get("scan_paths") or []:
        path = root / str(rel)
        if not path.is_file():
            errors.append(f"missing_scan_path: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for sub in forbidden:
            for i, line in enumerate(text.splitlines(), start=1):
                if _line_excluded(line, negation):
                    continue
                if sub in line:
                    errors.append(f"forbidden_substring {sub!r} in {rel} line {i}")
        for pat in forbidden_re:
            for i, line in enumerate(text.splitlines(), start=1):
                if _line_excluded(line, negation):
                    continue
                if pat.search(line):
                    errors.append(f"forbidden_regex {pat.pattern!r} in {rel} line {i}")
        for req in required_framing:
            if req not in text and rel.endswith(".md"):
                errors.append(f"missing_required_framing {req!r} in {rel}")

    for rel in post_bodies:
        path = root / rel
        if not path.is_file():
            errors.append(f"missing_post_body: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if not any(req in text for req in required_any_post):
            errors.append(f"missing_required_post_marker in {rel}")

    html = root / "reports" / "demo" / "gwangmyeong_baekje_daangn_paste_assistant_v1.html"
    if not html.is_file():
        errors.append("missing_html_demo")

    return errors


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", type=Path, default=CONTRACT)
    args = ap.parse_args()
    try:
        contract = load_contract(args.contract)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    errors = check_files(contract)
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: gwangmyeong_baekje daangn public copy contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
