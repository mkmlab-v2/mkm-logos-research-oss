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
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "docs" / "final" / "artifacts"

    status = _read_json(artifacts / "mkm_ai_status_pointer_latest.json")
    macro_smoke = _read_json(artifacts / "macro_risk_warning_api_smoke_latest.json")
    macro_policy = _read_json(artifacts / "macro_risk_warning_policy_binding_latest.json")
    showroom = _read_json(artifacts / "vps_24h_daemon_showroom_readiness_latest.json")

    payload = {
        "schema": "mkm_trackc_commercial_package_v1",
        "generated_at_utc": _utc_now(),
        "system_status": {
            "label": status.get("system_label"),
            "status": status.get("status"),
            "is_final": status.get("is_final"),
        },
        "package_readiness": {
            "macro_risk_api_smoke_present": bool(macro_smoke),
            "macro_risk_policy_present": bool(macro_policy),
            "showroom_readiness_present": bool(showroom),
        },
        "macro_risk_api": macro_smoke if macro_smoke else {"note": "missing artifact"},
        "macro_risk_policy": macro_policy if macro_policy else {"note": "missing artifact"},
        "showroom": showroom if showroom else {"note": "missing artifact"},
        "public_demo_urls": {
            "topology_radar_v1": "https://api.jemaai.cloud/public_showroom_topology_radar_v1.html",
            "board_minimal": "https://api.jemaai.cloud/public_showroom_board_minimal.html",
            "logos_research_v1": "https://api.jemaai.cloud/public_showroom_logos_research_v1.html",
            "note": "observational_only · NON_GATING · no_trade_signals · not investment advice",
        },
        "evidence": {
            "status_pointer": "docs/final/artifacts/mkm_ai_status_pointer_latest.json",
            "macro_risk_api_smoke": "docs/final/artifacts/macro_risk_warning_api_smoke_latest.json",
            "macro_risk_policy_binding": "docs/final/artifacts/macro_risk_warning_policy_binding_latest.json",
            "showroom_readiness": "docs/final/artifacts/vps_24h_daemon_showroom_readiness_latest.json",
        },
    }

    out_json = artifacts / "mkm_trackc_commercial_package_latest.json"
    out_md = artifacts / "mkm_trackc_commercial_package_latest.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# MKM Track C Commercial Package (Latest)",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- system_label: `{payload['system_status'].get('label')}`",
        f"- system_status: `{payload['system_status'].get('status')}`",
        f"- is_final: `{payload['system_status'].get('is_final')}`",
        f"- macro_risk_api_smoke_present: `{payload['package_readiness']['macro_risk_api_smoke_present']}`",
        f"- macro_risk_policy_present: `{payload['package_readiness']['macro_risk_policy_present']}`",
        f"- showroom_readiness_present: `{payload['package_readiness']['showroom_readiness_present']}`",
        "",
        "## Evidence Paths",
        "- `docs/final/artifacts/mkm_ai_status_pointer_latest.json`",
        "- `docs/final/artifacts/macro_risk_warning_api_smoke_latest.json`",
        "- `docs/final/artifacts/macro_risk_warning_policy_binding_latest.json`",
        "- `docs/final/artifacts/vps_24h_daemon_showroom_readiness_latest.json`",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"trackc package written: {out_json}")
    print(f"trackc brief written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
