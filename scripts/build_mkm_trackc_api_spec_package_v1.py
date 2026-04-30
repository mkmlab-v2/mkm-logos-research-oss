from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_error_contract(failure_drill: Dict[str, Any]) -> List[Dict[str, Any]]:
    cases = failure_drill.get("cases", [])
    out: List[Dict[str, Any]] = []
    for case in cases:
        result = case.get("result", {})
        out.append(
            {
                "case_name": case.get("name"),
                "error_signal": case.get("input", {}),
                "fallback_decision_state": result.get("decision_state"),
                "fallback_client_action": result.get("client_action"),
                "new_entry_policy": result.get("new_entry_policy"),
                "operator_notification_required": result.get("operator_notification_required"),
            }
        )
    return out


def main() -> int:
    root = Path("C:/workspace")
    artifacts = root / "docs" / "final" / "artifacts"

    onepager = _read_json(artifacts / "mkm_trackc_external_onepager_latest.json")
    contract = _read_json(artifacts / "macro_risk_warning_api_response_contract_v1.json")
    smoke = _read_json(artifacts / "macro_risk_warning_api_smoke_latest.json")
    policy = _read_json(artifacts / "macro_risk_warning_policy_binding_latest.json")
    failure = _read_json(artifacts / "macro_risk_warning_failure_drill_latest.json")

    if not onepager:
        raise SystemExit("missing onepager artifact: mkm_trackc_external_onepager_latest.json")
    if not contract:
        raise SystemExit("missing contract artifact: macro_risk_warning_api_response_contract_v1.json")

    field_contract = contract.get("field_contract", {})
    policy_result = policy.get("result", {}) if isinstance(policy.get("result"), dict) else {}

    spec = {
        "schema": "mkm_trackc_api_spec_package_v1",
        "generated_at_utc": _utc_now(),
        "api_name": "MKM Macro Risk Warning API",
        "version": "v1",
        "endpoint": {
            "method": "GET",
            "path": "/v1/macro-risk-warning",
            "query": {
                "asset_scope": "string (example: BTC-USD)",
            },
        },
        "request_contract": {
            "required_query_params": ["asset_scope"],
            "optional_headers": ["x-request-id"],
        },
        "response_contract_ref": "docs/final/artifacts/macro_risk_warning_api_response_contract_v1.json",
        "response_field_contract": field_contract,
        "live_snapshot": {
            "decision_state": smoke.get("decision_state"),
            "risk_warning_level": smoke.get("risk_warning_level"),
            "confidence_band": smoke.get("confidence_band"),
            "recommended_operator_posture": smoke.get("recommended_operator_posture"),
            "ttl_seconds": smoke.get("ttl_seconds"),
        },
        "policy_binding_snapshot": {
            "binding_status": policy_result.get("binding_status"),
            "client_action": policy_result.get("client_action"),
            "new_entry_policy": policy_result.get("new_entry_policy"),
            "operator_notification_required": policy_result.get("operator_notification_required"),
        },
        "error_handling_contract": _build_error_contract(failure),
        "sla_and_guardrails": {
            "signal_ttl_seconds": smoke.get("ttl_seconds", 900),
            "advisory_only": True,
            "operator_final_decision": True,
            "track_barrier": "Track A/B automatic bridge disabled",
        },
        "evidence_refs": onepager.get("evidence_refs", {}),
    }

    out_json = artifacts / "mkm_trackc_api_spec_package_latest.json"
    out_md = artifacts / "mkm_trackc_api_spec_package_latest.md"
    out_json.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# MKM Macro Risk Warning API Spec Package (v1)",
        "",
        f"- generated_at_utc: `{spec['generated_at_utc']}`",
        f"- endpoint: `{spec['endpoint']['method']} {spec['endpoint']['path']}`",
        "",
        "## Request Contract",
        "- required query: `asset_scope`",
        "- optional header: `x-request-id`",
        "",
        "## Response Snapshot (Live)",
        f"- decision_state: `{spec['live_snapshot'].get('decision_state')}`",
        f"- risk_warning_level: `{spec['live_snapshot'].get('risk_warning_level')}`",
        f"- confidence_band: `{spec['live_snapshot'].get('confidence_band')}`",
        f"- posture: `{spec['live_snapshot'].get('recommended_operator_posture')}`",
        f"- ttl_seconds: `{spec['live_snapshot'].get('ttl_seconds')}`",
        "",
        "## Policy Binding",
        f"- binding_status: `{spec['policy_binding_snapshot'].get('binding_status')}`",
        f"- client_action: `{spec['policy_binding_snapshot'].get('client_action')}`",
        f"- new_entry_policy: `{spec['policy_binding_snapshot'].get('new_entry_policy')}`",
        "",
        "## Error/Fallback Contract",
    ]
    for row in spec["error_handling_contract"]:
        md_lines.append(
            f"- `{row.get('case_name')}` -> `{row.get('fallback_decision_state')}` / "
            f"`{row.get('fallback_client_action')}`"
        )
    md_lines += [
        "",
        "## SLA and Guardrails",
        f"- signal_ttl_seconds: `{spec['sla_and_guardrails']['signal_ttl_seconds']}`",
        "- advisory_only: `True`",
        "- operator_final_decision: `True`",
        "- Track A/B automatic bridge disabled",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"api spec json written: {out_json}")
    print(f"api spec md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
