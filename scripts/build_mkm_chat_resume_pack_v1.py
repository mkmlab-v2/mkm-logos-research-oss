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

    dashboard = _read_json(art / "mkm_trackc_ops_dashboard_latest.json")
    acceptance = _read_json(art / "mkm_trackc_operational_acceptance_latest.json")

    resume = {
        "schema": "mkm_chat_resume_pack_v1",
        "generated_at_utc": _utc_now(),
        "quick_refs": {
            "central_memory": "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
            "ops_dashboard_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.md",
            "ops_dashboard_exec_md": "docs/final/artifacts/mkm_trackc_ops_dashboard_exec_latest.md",
            "acceptance_json": "docs/final/artifacts/mkm_trackc_operational_acceptance_latest.json",
            "runbook_checklist_md": "docs/final/artifacts/mkm_trackc_operations_runbook_checklist_latest.md",
            "core_prompt_gemini_athena": "docs/final/artifacts/MKM_CORE_PROMPT_GEMINI_ATHENA_V1.md",
        },
        "latest_status": {
            "system_status": (dashboard.get("system") or {}).get("status"),
            "promotion_decision": (dashboard.get("system") or {}).get("promotion_decision"),
            "trackc_packet_status": (dashboard.get("trackc") or {}).get("packet_status"),
            "acceptance_status": acceptance.get("status"),
        },
        "resume_commands": [
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_trackc_operational_acceptance.ps1",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Set-PaddleOnboardingStatus.ps1 -Status IN_PROGRESS -Note \"Payout/legal onboarding steps in progress.\"",
            "py scripts/build_mkm_chat_resume_pack_v1.py",
        ],
    }

    out_json = art / "mkm_chat_resume_pack_latest.json"
    out_md = art / "mkm_chat_resume_pack_latest.md"
    out_json.write_text(json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# MKM Chat Resume Pack",
        "",
        f"- generated_at_utc: `{resume['generated_at_utc']}`",
        f"- system_status: `{resume['latest_status'].get('system_status')}`",
        f"- promotion_decision: `{resume['latest_status'].get('promotion_decision')}`",
        f"- trackc_packet_status: `{resume['latest_status'].get('trackc_packet_status')}`",
        f"- acceptance_status: `{resume['latest_status'].get('acceptance_status')}`",
        "",
        "## Quick Refs",
    ]
    for _, path in resume["quick_refs"].items():
        md_lines.append(f"- `{path}`")
    md_lines += [
        "",
        "## Resume Commands",
        "- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_trackc_operational_acceptance.ps1`",
        "- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Set-PaddleOnboardingStatus.ps1 -Status IN_PROGRESS -Note \"Payout/legal onboarding steps in progress.\"`",
        "- `py scripts/build_mkm_chat_resume_pack_v1.py`",
    ]
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"resume pack json written: {out_json}")
    print(f"resume pack md written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
