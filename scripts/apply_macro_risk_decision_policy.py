#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.7, M:0.5}
# Balance: 90
# Purpose: Bind Macro Risk API decision_state to client action policy.
# Keywords: policy, decision_state, mapping, runtime, risk warning

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_decision_action_matrix_v1.json"
DEFAULT_RESPONSE = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_smoke_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_policy_binding_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"JSON file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _build_mapping_index(matrix_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = matrix_doc.get("mapping")
    if not isinstance(rows, list):
        raise ValueError("matrix.mapping must be a list")
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        state = str(row.get("decision_state", "")).strip()
        if state:
            out[state] = row
    return out


def _fallback_result(matrix_doc: dict[str, Any], reason: str) -> dict[str, Any]:
    fallback = matrix_doc.get("fallback_policy") or {}
    return {
        "binding_status": "fallback_applied",
        "reason": reason,
        "decision_state": "UNAVAILABLE",
        "client_action": fallback.get("client_action", "use_internal_safe_defaults_and_escalate"),
        "new_entry_policy": fallback.get("new_entry_policy", "restricted"),
        "operator_notification_required": bool(fallback.get("operator_notification_required", True)),
    }


def bind_policy(matrix_doc: dict[str, Any], response_doc: dict[str, Any]) -> dict[str, Any]:
    index = _build_mapping_index(matrix_doc)
    decision_state = str(response_doc.get("decision_state", "")).strip()
    if not decision_state:
        return _fallback_result(matrix_doc, reason="missing_decision_state")

    row = index.get(decision_state)
    if row is None:
        return _fallback_result(matrix_doc, reason=f"unmapped_decision_state:{decision_state}")

    return {
        "binding_status": "mapped",
        "reason": "ok",
        "decision_state": decision_state,
        "risk_warning_level": response_doc.get("risk_warning_level"),
        "recommended_operator_posture": row.get("recommended_operator_posture"),
        "client_action": row.get("client_action"),
        "new_entry_policy": row.get("new_entry_policy"),
        "risk_notes": row.get("risk_notes"),
        "operator_notification_required": decision_state in {"REDUCE_EXPOSURE", "FORCE_HOLD"},
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply Macro Risk decision policy binding.")
    p.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    p.add_argument("--response", type=Path, default=DEFAULT_RESPONSE)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    matrix_doc = _read_json(args.matrix if args.matrix.is_absolute() else (ROOT / args.matrix))
    response_doc = _read_json(args.response if args.response.is_absolute() else (ROOT / args.response))
    result = bind_policy(matrix_doc, response_doc)
    output = {
        "schema": "macro_risk_warning_policy_binding_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_refs": {
            "matrix": str(args.matrix),
            "response": str(args.response),
        },
        "result": result,
    }
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"policy_binding: PASS -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
