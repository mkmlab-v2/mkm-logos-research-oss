#!/usr/bin/env python3
"""Logos Studio B2B + agent-auth delegation bundle (tier_0, design lane).

Writes: reports/logos_studio_b2b_delegation_bundle_v1_latest.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1K = ROOT / "projects" / "no1kmedi"
OUT = ROOT / "reports" / "logos_studio_b2b_delegation_bundle_v1_latest.json"
PREFLIGHT = ROOT / "reports" / "mkm_high_delegation_preflight_v1_latest.json"
LIVE_SMOKE = ROOT / "reports" / "logos_agent_auth_live_smoke_v1_latest.json"
HD_OUT = ROOT / "reports" / "hd_autonomous_evolution_completion_v1_latest.json"

STEPS = [
    ("check_logos_auth_md", ["npm", "run", "check:logos-auth-md"], NO1K),
    ("smoke_logos_agent_auth", ["npm", "run", "smoke:logos-agent-auth"], NO1K),
    ("smoke_logos_agent_auth_live", ["npm", "run", "smoke:logos-agent-auth:live"], NO1K),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str], cwd: Path) -> dict:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)
    return {
        "step": name,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "cmd": " ".join(cmd),
        "tail": (proc.stdout or proc.stderr or "")[-400:],
    }


def main() -> int:
    preflight = {}
    if PREFLIGHT.is_file():
        preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))

    steps = [_run_step(n, c, d) for n, c, d in STEPS]
    all_ok = all(s["ok"] for s in steps)

    report = {
        "schema": "logos_studio_b2b_delegation_bundle_v1",
        "generated_at_utc": _now(),
        "lane": "design",
        "tier": "tier_0",
        "research_only": True,
        "send_gate": "HOLD",
        "mission_one_liner": "Logos B2B agent-auth demo pack + live smoke for WTP discovery",
        "preflight": {
            "ready_for_auto": preflight.get("ready_for_auto"),
            "host_ready": preflight.get("host_ready"),
            "browser_blocked": preflight.get("host_ready") is False,
        },
        "artifacts": {
            "demo_script": "reports/logos_studio_b2b_agent_auth_demo_script_v1.md",
            "playbook": "reports/logos_studio_b2b_wtp_discovery_call_playbook_v1.md",
            "auth_md_live": "https://logos.jema-ai.com/auth.md",
            "live_smoke": str(LIVE_SMOKE.relative_to(ROOT)).replace("\\", "/"),
        },
        "steps": steps,
        "ok": all_ok,
        "quality_ok": all_ok,
        "reproducible_command": "py scripts/run_logos_studio_b2b_delegation_bundle_v1.py",
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    hd = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _now(),
        "mission": report["mission_one_liner"],
        "lane": "design",
        "tier": "tier_0",
        "quality_ok": all_ok,
        "ok": all_ok,
        "bundle": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "reproducible_command": report["reproducible_command"],
        "preflight_note": "browser host_ready=false; tier_0 API/scripts only",
    }
    HD_OUT.write_text(json.dumps(hd, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"ok": all_ok, "out": str(OUT), "hd": str(HD_OUT)}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
