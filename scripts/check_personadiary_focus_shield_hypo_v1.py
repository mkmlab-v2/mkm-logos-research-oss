#!/usr/bin/env python3
"""PersonaDiary focus shield [HYPO] copy + bridge stub gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/final/artifacts/personadiary_focus_shield_hypo_v1_latest.json"
BRIDGE_SCHEMA = ROOT / "docs/final/schemas/personadiary_focus_shield_bridge_hypo_v1.schema.json"
BRIDGE_FIXTURE = ROOT / "tests/fixtures/personadiary_focus_shield_bridge_hypo_v1.example.json"
STUB_TS = ROOT / "projects/no1kmedi/src/lib/personadiaryScreenTimeBridgeStubHypoV1.ts"


def load_contract(path: Path = CONTRACT) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "personadiary_focus_shield_hypo_v1":
        raise ValueError(f"unexpected_contract_schema: {doc.get('schema')}")
    return doc


def _validate_bridge_fixture() -> list[str]:
    errors: list[str] = []
    if not BRIDGE_FIXTURE.is_file():
        return ["missing_bridge_fixture"]
    if not BRIDGE_SCHEMA.is_file():
        return ["missing_bridge_schema"]
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema_required"]
    instance = json.loads(BRIDGE_FIXTURE.read_text(encoding="utf-8-sig"))
    schema = json.loads(BRIDGE_SCHEMA.read_text(encoding="utf-8-sig"))
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"bridge_fixture_invalid: {exc.message}")
    return errors


def _check_ts_literals(contract: dict) -> list[str]:
    errors: list[str] = []
    required = contract.get("required_ts_literals") or {}
    if not STUB_TS.is_file():
        return ["missing_stub_ts"]
    text = STUB_TS.read_text(encoding="utf-8")
    for key, value in required.items():
        needle = f"{key}: {json.dumps(value)}"
        if needle not in text:
            errors.append(f"stub_ts missing literal {needle}")
    if "personadiary_focus_shield_bridge_hypo_v1" not in text:
        errors.append("stub_ts missing focus shield bridge schema id")
    return errors


def _check_scan_paths(contract: dict) -> list[str]:
    errors: list[str] = []
    forbidden = list(contract.get("forbidden_substrings") or [])
    anchor = str(contract.get("anchor_line_ko") or "")
    for rel in contract.get("scan_paths") or []:
        path = ROOT / str(rel)
        if not path.is_file():
            errors.append(f"missing_scan_path: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for sub in forbidden:
            if sub in text and not any(ex in text for ex in ("금지", "아님", "미연결", "stub")):
                errors.append(f"forbidden_substring {sub!r} in {rel}")
    if anchor and STUB_TS.is_file():
        pass
    hygiene = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryHygieneHypoPanel.tsx"
    if hygiene.is_file() and "stub" not in hygiene.read_text(encoding="utf-8").lower():
        errors.append("hygiene panel missing stub disclosure")
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

    errors: list[str] = []
    errors.extend(_validate_bridge_fixture())
    errors.extend(_check_ts_literals(contract))
    errors.extend(_check_scan_paths(contract))

    out = ROOT / "reports/personadiary_focus_shield_hypo_v1_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"ok": not errors, "errors": errors, "contract": str(CONTRACT)}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("OK: personadiary focus shield hypo contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
