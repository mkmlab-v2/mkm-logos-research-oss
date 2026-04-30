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

    package_path = artifacts / "mkm_trackc_commercial_package_latest.json"
    package = _read_json(package_path)
    if not package:
        raise SystemExit(f"missing or invalid package: {package_path}")

    system_status = package.get("system_status", {})
    readiness = package.get("package_readiness", {})
    macro = package.get("macro_risk_api", {})
    policy = package.get("macro_risk_policy", {}).get("result", {})
    showroom = package.get("showroom", {}).get("result", {})

    onepager = {
        "schema": "mkm_trackc_external_onepager_v1",
        "generated_at_utc": _utc_now(),
        "title": "MKM AI Track C: Macro Risk Warning API + Public Showroom",
        "elevator_pitch": "운영형 MKM AI의 거시 리스크 경보 API와 공개 쇼룸 레인을 결합한 고객 전달 패키지.",
        "current_state": {
            "system_label": system_status.get("label"),
            "status": system_status.get("status"),
            "is_final": system_status.get("is_final"),
        },
        "core_value": [
            "거시 리스크 신호를 구조화된 API 계약으로 제공",
            "결정 상태(WATCH/HOLD 등)와 운영자 포지셔닝 권고를 분리 표출",
            "공개 쇼룸과 비공개 운영 레인의 격벽 유지",
        ],
        "api_snapshot": {
            "decision_state": macro.get("decision_state"),
            "risk_warning_level": macro.get("risk_warning_level"),
            "confidence_band": macro.get("confidence_band"),
            "recommended_operator_posture": macro.get("recommended_operator_posture"),
            "ttl_seconds": macro.get("ttl_seconds"),
            "policy_binding_action": policy.get("client_action"),
        },
        "showroom_snapshot": {
            "overall_ready": showroom.get("overall_ready"),
            "go_no_go": showroom.get("go_no_go"),
        },
        "delivery_readiness": {
            "macro_risk_api_smoke_present": readiness.get("macro_risk_api_smoke_present"),
            "macro_risk_policy_present": readiness.get("macro_risk_policy_present"),
            "showroom_readiness_present": readiness.get("showroom_readiness_present"),
        },
        "guardrails": [
            "투자 자문 아님(운영 보조 신호)",
            "최종 의사결정은 운영자 책임",
            "Track A/B 자동 합선 금지",
        ],
        "evidence_refs": package.get("evidence", {}),
    }

    out_json = artifacts / "mkm_trackc_external_onepager_latest.json"
    out_md = artifacts / "mkm_trackc_external_onepager_latest.md"
    out_json.write_text(json.dumps(onepager, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# MKM AI Track C External One-Pager",
        "",
        f"- generated_at_utc: `{onepager['generated_at_utc']}`",
        f"- title: `{onepager['title']}`",
        f"- status: `{onepager['current_state'].get('status')}`",
        "",
        "## Elevator Pitch",
        onepager["elevator_pitch"],
        "",
        "## Core Value",
        f"- {onepager['core_value'][0]}",
        f"- {onepager['core_value'][1]}",
        f"- {onepager['core_value'][2]}",
        "",
        "## API Snapshot",
        f"- decision_state: `{onepager['api_snapshot'].get('decision_state')}`",
        f"- risk_warning_level: `{onepager['api_snapshot'].get('risk_warning_level')}`",
        f"- confidence_band: `{onepager['api_snapshot'].get('confidence_band')}`",
        f"- posture: `{onepager['api_snapshot'].get('recommended_operator_posture')}`",
        f"- policy_binding_action: `{onepager['api_snapshot'].get('policy_binding_action')}`",
        "",
        "## Showroom Snapshot",
        f"- overall_ready: `{onepager['showroom_snapshot'].get('overall_ready')}`",
        f"- go_no_go: `{onepager['showroom_snapshot'].get('go_no_go')}`",
        "",
        "## Delivery Readiness",
        f"- macro_risk_api_smoke_present: `{onepager['delivery_readiness'].get('macro_risk_api_smoke_present')}`",
        f"- macro_risk_policy_present: `{onepager['delivery_readiness'].get('macro_risk_policy_present')}`",
        f"- showroom_readiness_present: `{onepager['delivery_readiness'].get('showroom_readiness_present')}`",
        "",
        "## Guardrails",
        f"- {onepager['guardrails'][0]}",
        f"- {onepager['guardrails'][1]}",
        f"- {onepager['guardrails'][2]}",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"onepager json written: {out_json}")
    print(f"onepager md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
