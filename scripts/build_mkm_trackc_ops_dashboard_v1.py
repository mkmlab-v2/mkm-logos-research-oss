from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    root = Path("C:/workspace")
    art = root / "docs" / "final" / "artifacts"

    status = _read_json(art / "mkm_ai_status_pointer_latest.json")
    decision = _read_json(art / "mkm_ai_v2_promotion_decision_latest.json")
    handoff = _read_json(art / "mkm_trackc_client_handoff_package_latest.json")
    acceptance = _read_json(art / "mkm_trackc_operational_acceptance_latest.json")
    freeze = _read_json(art / "mkm_trackc_delivery_freeze_log_latest.json")
    guard = _read_json(art / "mkm_trackc_client_handoff_guard_latest.json")
    drill = _read_json(art / "mkm_trackc_guard_recovery_drill_latest.json")
    paddle = _read_json(art / "paddle_onboarding_status_latest.json")

    dashboard = {
        "schema": "mkm_trackc_ops_dashboard_v1",
        "generated_at_utc": _utc_now(),
        "system": {
            "label": status.get("system_label"),
            "status": status.get("status"),
            "is_final": status.get("is_final"),
            "promotion_decision": decision.get("decision"),
            "promotion_ready": decision.get("promotion_ready"),
            "weekly_pass_rate_percent": status.get("weekly_pass_rate_percent"),
            "weekly_sample_count": status.get("weekly_sample_count"),
        },
        "trackc": {
            "packet_status": handoff.get("packet_status"),
            "api_decision_state": (handoff.get("executive_summary") or {}).get("api_decision_state"),
            "showroom_go_no_go": (handoff.get("executive_summary") or {}).get("showroom_go_no_go"),
            "guard_passed": guard.get("passed"),
            "acceptance_status": acceptance.get("status"),
            "freeze_status": freeze.get("status"),
            "recovery_drill_status": drill.get("status"),
            "paddle_runbook_present": (art / "PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md").exists(),
            "paddle_onboarding_status": paddle.get("status", "RUNBOOK_READY"),
        },
        "evidence": {
            "status_pointer": "docs/final/artifacts/mkm_ai_status_pointer_latest.json",
            "promotion_decision": "docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json",
            "handoff_package": "docs/final/artifacts/mkm_trackc_client_handoff_package_latest.json",
            "handoff_guard": "docs/final/artifacts/mkm_trackc_client_handoff_guard_latest.json",
            "acceptance": "docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json",
            "freeze_log": "docs/final/artifacts/mkm_trackc_delivery_freeze_log_latest.json",
            "recovery_drill": "docs/final/artifacts/mkm_trackc_guard_recovery_drill_latest.json",
            "paddle_onboarding_runbook": "docs/final/artifacts/PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md",
            "paddle_onboarding_status": "docs/final/artifacts/paddle_onboarding_status_latest.json",
        },
    }

    out_json = art / "mkm_trackc_ops_dashboard_latest.json"
    out_md = art / "mkm_trackc_ops_dashboard_latest.md"
    out_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# MKM Track C Ops Dashboard",
        "",
        f"- generated_at_utc: `{dashboard['generated_at_utc']}`",
        f"- system_status: `{dashboard['system']['status']}`",
        f"- promotion_decision: `{dashboard['system']['promotion_decision']}`",
        f"- promotion_ready: `{dashboard['system']['promotion_ready']}`",
        f"- weekly_pass_rate_percent: `{dashboard['system']['weekly_pass_rate_percent']}`",
        f"- weekly_sample_count: `{dashboard['system']['weekly_sample_count']}`",
        "",
        "## Track C",
        f"- packet_status: `{dashboard['trackc']['packet_status']}`",
        f"- api_decision_state: `{dashboard['trackc']['api_decision_state']}`",
        f"- showroom_go_no_go: `{dashboard['trackc']['showroom_go_no_go']}`",
        f"- guard_passed: `{dashboard['trackc']['guard_passed']}`",
        f"- acceptance_status: `{dashboard['trackc']['acceptance_status']}`",
        f"- freeze_status: `{dashboard['trackc']['freeze_status']}`",
        f"- recovery_drill_status: `{dashboard['trackc']['recovery_drill_status']}`",
        f"- paddle_runbook_present: `{dashboard['trackc']['paddle_runbook_present']}`",
        f"- paddle_onboarding_status: `{dashboard['trackc']['paddle_onboarding_status']}`",
        "",
        "## Evidence",
        "- `docs/final/artifacts/mkm_ai_status_pointer_latest.json`",
        "- `docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_client_handoff_package_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_client_handoff_guard_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_delivery_freeze_log_latest.json`",
        "- `docs/final/artifacts/mkm_trackc_guard_recovery_drill_latest.json`",
        "- `docs/final/artifacts/PADDLE_ONBOARDING_SECURE_RUNBOOK_V1.md`",
        "- `docs/final/artifacts/paddle_onboarding_status_latest.json`",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"dashboard json written: {out_json}")
    print(f"dashboard md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
