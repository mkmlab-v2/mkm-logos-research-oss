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
    guard = _read_json(art / "mkm_trackc_client_handoff_guard_latest.json")
    acceptance = _read_json(art / "mkm_trackc_operational_acceptance_latest.json")
    freeze = _read_json(art / "mkm_trackc_delivery_freeze_log_latest.json")
    dashboard = _read_json(art / "mkm_trackc_ops_dashboard_latest.json")

    checklist = {
        "schema": "mkm_trackc_operations_runbook_checklist_v1",
        "generated_at_utc": _utc_now(),
        "checks": [
            {"id": "system_final", "ok": status.get("status") == "APPROVED_FINAL_V2"},
            {"id": "promotion_go", "ok": status.get("decision") == "GO_FINAL_V2"},
            {"id": "handoff_guard_pass", "ok": guard.get("passed") is True},
            {"id": "acceptance_pass", "ok": acceptance.get("status") == "PASS"},
            {"id": "freeze_frozen", "ok": freeze.get("status") == "FROZEN"},
            {"id": "packet_ready", "ok": (dashboard.get("trackc") or {}).get("packet_status") == "READY"},
        ],
    }
    checklist["all_ok"] = all(c["ok"] for c in checklist["checks"])

    out_json = art / "mkm_trackc_operations_runbook_checklist_latest.json"
    out_md = art / "mkm_trackc_operations_runbook_checklist_latest.md"
    out_json.write_text(json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# MKM Track C Operations Runbook Checklist",
        "",
        f"- generated_at_utc: `{checklist['generated_at_utc']}`",
        f"- all_ok: `{checklist['all_ok']}`",
        "",
        "## Final Readiness Checks",
    ]
    for c in checklist["checks"]:
        mark = "PASS" if c["ok"] else "FAIL"
        lines.append(f"- [{mark}] `{c['id']}`")
    lines += [
        "",
        "## Run Commands",
        "- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_trackc_operational_acceptance.ps1`",
        "- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_workspace_automation_health.ps1 -SkipVaultMirror -SkipMkmMemoryInventory -SkipPhase1Readiness -SkipNewsObservationContractSmoke -IncludeMkmAiV2Readiness -IncludeMkmAiFinalOpsGuard -IncludeMkmAiTrackCHandoffGuard`",
        "",
        "## Incident Action",
        "- If any check fails: run acceptance chain once, inspect guard/freeze artifacts, then re-check.",
    ]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"runbook checklist json written: {out_json}")
    print(f"runbook checklist md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
