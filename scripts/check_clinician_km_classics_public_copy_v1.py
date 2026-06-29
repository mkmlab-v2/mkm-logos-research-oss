#!/usr/bin/env python3
"""D2: Clinician km-classics PUBLIC_FACING copy gate [HYPO]."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/final/artifacts/clinician_km_classics_copy_contract_v1_latest.json"


def load_contract(path: Path = CONTRACT) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "clinician_km_classics_copy_contract_v1":
        raise ValueError(f"unexpected_contract_schema: {doc.get('schema')}")
    return doc


def check_files(contract: dict, *, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    forbidden = list(contract.get("forbidden_substrings") or [])
    required_any = ["원장 검토 초안"]
    for rel in contract.get("scan_paths") or []:
        path = root / str(rel)
        if not path.is_file():
            errors.append(f"missing_scan_path: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for sub in forbidden:
            if sub in text:
                errors.append(f"forbidden_substring {sub!r} in {rel}")
        if not any(req in text for req in required_any):
            errors.append(f"missing_required_framing {required_any!r} in {rel}")
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
    print("OK: clinician km-classics public copy contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
