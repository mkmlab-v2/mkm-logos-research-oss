from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    root = Path("C:/workspace")
    artifacts = root / "docs" / "final" / "artifacts"

    commercial = _read_json(artifacts / "mkm_trackc_commercial_package_latest.json")
    onepager = _read_json(artifacts / "mkm_trackc_external_onepager_latest.json")
    api_spec = _read_json(artifacts / "mkm_trackc_api_spec_package_latest.json")

    if not commercial:
        raise SystemExit("missing commercial package")
    if not onepager:
        raise SystemExit("missing external onepager")
    if not api_spec:
        raise SystemExit("missing api spec package")

    readiness = commercial.get("package_readiness", {})
    ready_all = all(
        bool(readiness.get(k))
        for k in (
            "macro_risk_api_smoke_present",
            "macro_risk_policy_present",
            "showroom_readiness_present",
        )
    )

    packet = {
        "schema": "mkm_trackc_client_handoff_package_v1",
        "generated_at_utc": _utc_now(),
        "packet_status": "READY" if ready_all else "PARTIAL",
        "title": "MKM AI Track C Client Handoff Package",
        "executive_summary": {
            "status": onepager.get("current_state", {}).get("status"),
            "elevator_pitch": onepager.get("elevator_pitch"),
            "api_decision_state": onepager.get("api_snapshot", {}).get("decision_state"),
            "showroom_go_no_go": onepager.get("showroom_snapshot", {}).get("go_no_go"),
        },
        "delivery_checklist": {
            "commercial_package_ready": bool(commercial),
            "external_onepager_ready": bool(onepager),
            "api_spec_package_ready": bool(api_spec),
            "macro_risk_api_smoke_present": readiness.get("macro_risk_api_smoke_present"),
            "macro_risk_policy_present": readiness.get("macro_risk_policy_present"),
            "showroom_readiness_present": readiness.get("showroom_readiness_present"),
        },
        "api_contract_quickview": {
            "endpoint": api_spec.get("endpoint", {}),
            "request_contract": api_spec.get("request_contract", {}),
            "live_snapshot": api_spec.get("live_snapshot", {}),
            "policy_binding_snapshot": api_spec.get("policy_binding_snapshot", {}),
            "sla_and_guardrails": api_spec.get("sla_and_guardrails", {}),
        },
        "artifacts": {
            "commercial_package_json": "docs/final/artifacts/mkm_trackc_commercial_package_latest.json",
            "commercial_package_md": "docs/final/artifacts/mkm_trackc_commercial_package_latest.md",
            "external_onepager_json": "docs/final/artifacts/mkm_trackc_external_onepager_latest.json",
            "external_onepager_md": "docs/final/artifacts/mkm_trackc_external_onepager_latest.md",
            "api_spec_package_json": "docs/final/artifacts/mkm_trackc_api_spec_package_latest.json",
            "api_spec_package_md": "docs/final/artifacts/mkm_trackc_api_spec_package_latest.md",
        },
    }

    out_json = artifacts / "mkm_trackc_client_handoff_package_latest.json"
    out_md = artifacts / "mkm_trackc_client_handoff_package_latest.md"
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# MKM AI Track C Client Handoff Package",
        "",
        f"- generated_at_utc: `{packet['generated_at_utc']}`",
        f"- packet_status: `{packet['packet_status']}`",
        f"- status: `{packet['executive_summary'].get('status')}`",
        f"- api_decision_state: `{packet['executive_summary'].get('api_decision_state')}`",
        f"- showroom_go_no_go: `{packet['executive_summary'].get('showroom_go_no_go')}`",
        "",
        "## Elevator Pitch",
        packet["executive_summary"].get("elevator_pitch", ""),
        "",
        "## Delivery Checklist",
        f"- commercial_package_ready: `{packet['delivery_checklist']['commercial_package_ready']}`",
        f"- external_onepager_ready: `{packet['delivery_checklist']['external_onepager_ready']}`",
        f"- api_spec_package_ready: `{packet['delivery_checklist']['api_spec_package_ready']}`",
        f"- macro_risk_api_smoke_present: `{packet['delivery_checklist']['macro_risk_api_smoke_present']}`",
        f"- macro_risk_policy_present: `{packet['delivery_checklist']['macro_risk_policy_present']}`",
        f"- showroom_readiness_present: `{packet['delivery_checklist']['showroom_readiness_present']}`",
        "",
        "## Artifact Paths",
        "- `docs/final/artifacts/mkm_trackc_commercial_package_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_external_onepager_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_api_spec_package_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_client_handoff_package_latest.json`",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"handoff json written: {out_json}")
    print(f"handoff md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
