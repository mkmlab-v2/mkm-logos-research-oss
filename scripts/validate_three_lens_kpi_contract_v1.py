#!/usr/bin/env python3
"""Validate three-lens KPI contract shape for staged governance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "docs" / "final" / "artifacts" / "THREE_LENS_KPI_CONTRACT_V1.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate_lens_block(name: str, block: dict) -> list[str]:
    errors: list[str] = []
    required_metrics = block.get("required_metrics")
    pass_thresholds = block.get("pass_thresholds")
    auto_demote_conditions = block.get("auto_demote_conditions")
    if not isinstance(required_metrics, list) or not required_metrics:
        errors.append(f"{name}.required_metrics must be non-empty list")
    if not isinstance(pass_thresholds, dict) or not pass_thresholds:
        errors.append(f"{name}.pass_thresholds must be non-empty object")
    if not isinstance(auto_demote_conditions, list) or not auto_demote_conditions:
        errors.append(f"{name}.auto_demote_conditions must be non-empty list")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract-json", type=Path, default=DEFAULT_CONTRACT)
    args = ap.parse_args()

    contract_path = args.contract_json if args.contract_json.is_absolute() else ROOT / args.contract_json
    if not contract_path.is_file():
        print(f"Missing contract: {contract_path}")
        return 2

    doc = _load_json(contract_path)
    errors: list[str] = []
    if doc.get("schema") != "three_lens_kpi_contract_v1":
        errors.append("schema must be three_lens_kpi_contract_v1")
    if str(doc.get("track") or "").upper() != "B_TRACK":
        errors.append("track must be B_TRACK")
    policy = doc.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be object")
    else:
        if policy.get("logos_non_gating_required") is not True:
            errors.append("policy.logos_non_gating_required must be true")
        if policy.get("field_ops_precedence") is not True:
            errors.append("policy.field_ops_precedence must be true")

    lenses = doc.get("lenses")
    if not isinstance(lenses, dict):
        errors.append("lenses must be object")
    else:
        for lens in ("sasang", "myeongni", "logos"):
            block = lenses.get(lens)
            if not isinstance(block, dict):
                errors.append(f"lenses.{lens} must be object")
                continue
            errors.extend(_validate_lens_block(lens, block))

    gate = doc.get("promotion_gate")
    if not isinstance(gate, dict):
        errors.append("promotion_gate must be object")
    else:
        if gate.get("all_lens_pass_required") is not True:
            errors.append("promotion_gate.all_lens_pass_required must be true")
        if gate.get("human_signoff_required") is not True:
            errors.append("promotion_gate.human_signoff_required must be true")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({"ok": True, "contract": str(contract_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
