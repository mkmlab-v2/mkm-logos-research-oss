#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic governance classifier for MKM_DELEGATED_EXECUTION_GOVERNANCE_V1.

Deterministic case table only — no scientific validity judgment.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_MD = ROOT / "docs" / "final" / "MKM_DELEGATED_EXECUTION_POLICY_V1.md"
POLICY_JSON = (
    ROOT / "docs" / "final" / "artifacts" / "mkm_delegated_execution_policy_v1_latest.json"
)
OUT = (
    ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "mkm_delegated_execution_governance_synthetic_v1_latest.json"
)

CASES = [
    {"id": 1, "action": "read_only_forensic", "expected": "GREEN_CONTINUE"},
    {"id": 2, "action": "bounded_impl_plus_dev_test", "expected": "GREEN_CONTINUE"},
    {
        "id": 3,
        "action": "independent_impl_validator_pass",
        "expected": "GREEN_SEAL_NO_SEMANTIC_PROMOTION",
    },
    {"id": 4, "action": "independent_validator_fail", "expected": "SEAL_AND_STOP"},
    {
        "id": 5,
        "action": "real_heldout_semantic_execution",
        "expected": "YELLOW_COMMANDER_REQUIRED",
    },
    {
        "id": 6,
        "action": "fail_then_patch_then_rerun_as_fresh",
        "expected": "NOT_FRESH_COMMANDER_REQUIRED",
    },
    {"id": 7, "action": "deploy_production", "expected": "RED_BLOCK"},
    {"id": 8, "action": "trade_or_send_or_payment", "expected": "RED_BLOCK"},
    {
        "id": 9,
        "action": "sealed_first_result_overwrite",
        "expected": "RED_BLOCK",
    },
    {
        "id": 10,
        "action": "missing_authoritative_artifact",
        "expected": "UNKNOWN_AND_STOP",
    },
    {
        "id": 11,
        "action": "builder_pass_without_validator",
        "expected": "BUILDER_REPORTED_ONLY",
    },
    {
        "id": 12,
        "action": "impl_pass_claims_effectiveness",
        "expected": "BLOCK_CEILING_VIOLATION",
    },
    {
        "id": 13,
        "action": "green_forensic_impl_code_validator_chain",
        "expected": "GREEN_CONTINUE",
    },
    {
        "id": 14,
        "action": "green_reconciliation_to_code_validator",
        "expected": "GREEN_CONTINUE",
    },
    {
        "id": 15,
        "action": "green_subtask_done_alone",
        "expected": "GREEN_CONTINUE",
    },
    {
        "id": 16,
        "action": "validator_partial",
        "expected": "SEAL_AND_STOP",
    },
]


def classify(action: str) -> str:
    table = {
        "read_only_forensic": "GREEN_CONTINUE",
        "bounded_impl_plus_dev_test": "GREEN_CONTINUE",
        "independent_impl_validator_pass": "GREEN_SEAL_NO_SEMANTIC_PROMOTION",
        "independent_validator_fail": "SEAL_AND_STOP",
        "real_heldout_semantic_execution": "YELLOW_COMMANDER_REQUIRED",
        "fail_then_patch_then_rerun_as_fresh": "NOT_FRESH_COMMANDER_REQUIRED",
        "deploy_production": "RED_BLOCK",
        "trade_or_send_or_payment": "RED_BLOCK",
        "sealed_first_result_overwrite": "RED_BLOCK",
        "missing_authoritative_artifact": "UNKNOWN_AND_STOP",
        "builder_pass_without_validator": "BUILDER_REPORTED_ONLY",
        "impl_pass_claims_effectiveness": "BLOCK_CEILING_VIOLATION",
        "green_forensic_impl_code_validator_chain": "GREEN_CONTINUE",
        "green_reconciliation_to_code_validator": "GREEN_CONTINUE",
        "green_subtask_done_alone": "GREEN_CONTINUE",
        "validator_partial": "SEAL_AND_STOP",
    }
    return table[action]


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    results = []
    pass_count = 0
    fail_count = 0
    for case in CASES:
        got = classify(case["action"])
        ok = got == case["expected"]
        if ok:
            pass_count += 1
        else:
            fail_count += 1
        results.append(
            {
                "id": case["id"],
                "action": case["action"],
                "expected": case["expected"],
                "got": got,
                "pass": ok,
            }
        )

    payload = {
        "schema": "mkm_delegated_execution_governance_synthetic_v1",
        "mission": "MKM_DELEGATED_EXECUTION_GOVERNANCE_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy_md": str(POLICY_MD.relative_to(ROOT)).replace("\\", "/"),
        "policy_md_sha256": sha256_file(POLICY_MD),
        "policy_json_sha256": sha256_file(POLICY_JSON),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "all_pass": fail_count == 0,
        "cases": results,
        "LIVE": False,
        "SEND": False,
        "DEPLOY": False,
        "TRADE": False,
        "SEMANTIC_EXECUTION": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS={pass_count} FAIL={fail_count} OUT={OUT}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
