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


def _promotion_decision_agent_label(decision: str | None) -> str | None:
    """Agent-facing alias — avoids GO_FINAL_V2 misread as customer SEND/live GO."""
    if not decision:
        return None
    labels = {
        "GO_FINAL_V2": "INTERNAL_V2_READY",
        "HOLD": "HOLD",
        "GO": "INTERNAL_GO",
        "NO_GO": "NO_GO",
    }
    return labels.get(str(decision), str(decision))


def main() -> int:
    root = Path("C:/workspace")
    art = root / "docs" / "final" / "artifacts"
    dashboard = _read_json(art / "mkm_trackc_ops_dashboard_latest.json")
    if not dashboard:
        raise SystemExit("missing mkm_trackc_ops_dashboard_latest.json")

    system = dashboard.get("system", {})
    trackc = dashboard.get("trackc", {})
    decision = system.get("promotion_decision")
    agent_label = _promotion_decision_agent_label(decision)

    out = art / "mkm_trackc_ops_dashboard_exec_latest.md"
    lines = [
        "# MKM Track C Executive Snapshot",
        "",
        f"- generated_at_utc: `{_utc_now()}`",
        f"- system: `{system.get('status')}` / decision `{decision}` (agent: `{agent_label}` — not SEND/live)",
        f"- readiness: `{system.get('weekly_pass_rate_percent')}%` ({system.get('weekly_sample_count')} samples)",
        f"- packet: `{trackc.get('packet_status')}` / guard `{trackc.get('guard_passed')}`",
        f"- acceptance: `{trackc.get('acceptance_status')}` / freeze `{trackc.get('freeze_status')}`",
        f"- recovery drill: `{trackc.get('recovery_drill_status')}`",
        "",
        "## Go/No-Go",
        "- `GO` when all lines above remain green (`APPROVED_FINAL_V2`, `INTERNAL_V2_READY`, `READY`, guard true, acceptance PASS, freeze FROZEN).",
        "- `HOLD` if any single item degrades; re-run acceptance chain after remediation.",
        "- `promotion_decision` machine value may remain `GO_FINAL_V2`; agent label `INTERNAL_V2_READY` is not customer SEND.",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"exec dashboard written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
