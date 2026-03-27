#!/usr/bin/env python3
"""Validate dual-track master codebook JSON against operational guardrails.

This validator is intentionally dependency-free for CI portability.
It enforces:
- lookup/training physical separation
- OFF-by-default hybrid experiment flags
- literal restoration 100% governance requirement
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_SCHEMA = WORKSPACE_ROOT / "docs" / "final" / "master_codebook_dual_track.schema.json"
DEFAULT_INSTANCE = WORKSPACE_ROOT / "docs" / "final" / "master_codebook_dual_track.template.json"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _ensure(condition: bool, msg: str, errors: list[str]) -> None:
    if not condition:
        errors.append(msg)


def _validate_instance(payload: dict[str, Any], errors: list[str]) -> None:
    required_top = ["schema_version", "codebook_id", "lookup", "training", "hybrid_experiment", "governance"]
    for key in required_top:
        _ensure(key in payload, f"missing top-level field: {key}", errors)
    if errors:
        return

    lookup = payload["lookup"]
    training = payload["training"]
    hybrid = payload["hybrid_experiment"]
    governance = payload["governance"]

    _ensure(isinstance(lookup, dict), "lookup must be object", errors)
    _ensure(isinstance(training, dict), "training must be object", errors)
    _ensure(isinstance(hybrid, dict), "hybrid_experiment must be object", errors)
    _ensure(isinstance(governance, dict), "governance must be object", errors)
    if errors:
        return

    _ensure(lookup.get("ssot_locked") is True, "lookup.ssot_locked must be true", errors)
    entries = lookup.get("entries")
    _ensure(isinstance(entries, list) and len(entries) > 0, "lookup.entries must be non-empty array", errors)
    if isinstance(entries, list):
        seen_lookup_ids: set[str] = set()
        for i, row in enumerate(entries):
            if not isinstance(row, dict):
                errors.append(f"lookup.entries[{i}] must be object")
                continue
            lid = row.get("lookup_id")
            _ensure(isinstance(lid, str) and len(lid) > 0, f"lookup.entries[{i}].lookup_id invalid", errors)
            if isinstance(lid, str) and lid:
                _ensure(lid not in seen_lookup_ids, f"duplicate lookup_id: {lid}", errors)
                seen_lookup_ids.add(lid)

    records = training.get("records")
    _ensure(isinstance(training.get("enabled"), bool), "training.enabled must be boolean", errors)
    _ensure(isinstance(records, list), "training.records must be array", errors)
    lookup_ids = {
        row.get("lookup_id")
        for row in entries
        if isinstance(row, dict) and isinstance(row.get("lookup_id"), str)
    } if isinstance(entries, list) else set()
    if isinstance(records, list):
        for i, row in enumerate(records):
            if not isinstance(row, dict):
                errors.append(f"training.records[{i}] must be object")
                continue
            for req in ["training_id", "lookup_id_ref", "prompt", "response", "split", "quality_gate_passed"]:
                _ensure(req in row, f"training.records[{i}] missing field: {req}", errors)
            lref = row.get("lookup_id_ref")
            if isinstance(lref, str):
                _ensure(lref in lookup_ids, f"training.records[{i}].lookup_id_ref not found in lookup: {lref}", errors)

    for flag in ["enabled", "quaternion_transition_enabled", "threshold_gate_enabled"]:
        _ensure(hybrid.get(flag) is False, f"hybrid_experiment.{flag} must be false by default", errors)

    _ensure(
        governance.get("literal_restoration_rate_required") == 100.0,
        "governance.literal_restoration_rate_required must be 100.0",
        errors,
    )
    _ensure(
        governance.get("off_by_default_policy") is True,
        "governance.off_by_default_policy must be true",
        errors,
    )
    pr = governance.get("promotion_rules")
    _ensure(isinstance(pr, dict), "governance.promotion_rules must be object", errors)
    if isinstance(pr, dict):
        for k in [
            "require_min_recall_non_degradation",
            "require_brier_non_degradation",
            "require_ci_stability",
        ]:
            _ensure(pr.get(k) is True, f"governance.promotion_rules.{k} must be true", errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dual-track master codebook schema and instance")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="Path to schema JSON")
    parser.add_argument("--instance", default=str(DEFAULT_INSTANCE), help="Path to instance/template JSON")
    args = parser.parse_args()

    schema_path = Path(args.schema)
    if not schema_path.is_absolute():
        schema_path = WORKSPACE_ROOT / schema_path
    inst_path = Path(args.instance)
    if not inst_path.is_absolute():
        inst_path = WORKSPACE_ROOT / inst_path

    errors: list[str] = []
    if not schema_path.is_file():
        errors.append(f"schema not found: {schema_path}")
    if not inst_path.is_file():
        errors.append(f"instance not found: {inst_path}")
    if errors:
        print("❌ validation failed")
        for e in errors:
            print(f"- {e}")
        return 1

    try:
        schema = _load_json(schema_path)
    except Exception as e:
        print(f"❌ schema json parse failed: {e}")
        return 1
    try:
        instance = _load_json(inst_path)
    except Exception as e:
        print(f"❌ instance json parse failed: {e}")
        return 1

    schema_required = schema.get("required", [])
    if not isinstance(schema_required, list) or not schema_required:
        errors.append("schema.required must be non-empty array")

    if not isinstance(instance, dict):
        errors.append("instance must be top-level object")
    else:
        _validate_instance(instance, errors)

    if errors:
        print("❌ validation failed")
        for e in errors:
            print(f"- {e}")
        return 1

    print("✅ dual-track codebook validation passed")
    print(f"schema: {schema_path.resolve()}")
    print(f"instance: {inst_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
