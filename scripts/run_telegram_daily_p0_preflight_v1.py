#!/usr/bin/env python3
"""Telegram daily P0 preflight — shock policy + morning brief before 08:28 send.

  py scripts/run_telegram_daily_p0_preflight_v1.py

Outputs: reports/telegram_daily_wiring_v1_latest.json
P3 hard lock: no Track A / live / SEND promotion wiring.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/telegram_daily_wiring_v1_latest.json"
P1_WIRING = ROOT / "reports/p1_advisory_ops_wiring_v1_latest.json"
SHOCK = ROOT / "docs/final/artifacts/kospi_shock_conditional_attach_operator_policy_v1_latest.json"
BRIEF = ROOT / "docs/final/artifacts/internal_kospi_morning_brief_onepager_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(label: str, cmd: list[str]) -> dict[str, Any]:
    print(f"==> [{label}]", " ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=str(ROOT))
    return {"label": label, "exit_code": rc, "cmd": cmd, "ok": rc == 0}


def _build_p1_wiring() -> dict[str, Any]:
    shock = _read(SHOCK)
    brief = _read(BRIEF)
    return {
        "schema": "p1_advisory_ops_wiring_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "excluded_from_final_call": True,
        "gate_mode": "warning",
        "track_a_promotion_approved": False,
        "live_trading_approved": False,
        "wiring": {
            "operator_posture_source": str(SHOCK.relative_to(ROOT)).replace("\\", "/"),
            "morning_brief_source": str(BRIEF.relative_to(ROOT)).replace("\\", "/"),
            "telegram_daily_wiring": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "snapshot": {
            "attach_mode": ((brief or {}).get("field_final_call") or {}).get("attach_mode"),
            "today_action": (brief or {}).get("today_action"),
            "operator_posture": (shock or {}).get("today_evaluation", {}).get("operator_posture")
            or ((brief or {}).get("field_final_call") or {}).get("operator_posture"),
        },
        "forbidden": [
            "Final Call auto-merge from sidebar",
            "Track A promotion from telegram wiring",
            "live order keys",
        ],
        "reproduce": "py scripts/run_telegram_daily_p0_preflight_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-build", action="store_true", help="Manifest only from existing artifacts")
    args = ap.parse_args()

    py = sys.executable
    steps: dict[str, Any] = {}
    ok = True

    if not args.skip_build:
        for key, script in (
            ("p0_shock_policy", "scripts/build_kospi_shock_conditional_attach_operator_policy_v1.py"),
            ("p0_morning_brief", "scripts/build_internal_kospi_morning_brief_onepager_v1.py"),
        ):
            steps[key] = _run(key, [py, str(ROOT / script)])
            ok = ok and steps[key]["ok"]

    p1 = _build_p1_wiring()
    P1_WIRING.parent.mkdir(parents=True, exist_ok=True)
    P1_WIRING.write_text(json.dumps(p1, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    steps["p1_advisory_wiring"] = {"ok": True, "artifact": str(P1_WIRING)}

    brief = _read(BRIEF) or {}
    field = brief.get("field_final_call") or {}
    doc = {
        "schema": "telegram_daily_wiring_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "gate_mode": "warning",
        "cost_tier": "tier_0",
        "p3_hard_lock": {
            "track_a_promotion_approved": False,
            "live_trading_approved": False,
            "send_gate": "HOLD",
            "final_call_auto_merge": False,
            "p3_forbidden": True,
        },
        "telegram_contract": {
            "refresh_hook": "scripts/Invoke-TelegramMorningProphecyRefresh_v1.ps1",
            "send_hook": "scripts/Invoke-TelegramMinimalDailyDigest_v1.ps1",
            "digest_style": "prophecy",
            "field_final_call_in_digest": True,
            "lens_sidebar_non_gating": True,
            "morning_brief_schema_revision": brief.get("schema_revision"),
        },
        "snapshot": {
            "today_action": brief.get("today_action"),
            "attach_mode": field.get("attach_mode"),
            "operator_posture": field.get("operator_posture"),
            "promotion_decision": brief.get("promotion_decision"),
        },
        "steps": steps,
        "ok": ok and bool(brief.get("today_action")),
        "artifacts": {
            "wiring_manifest": str(OUT.relative_to(ROOT)).replace("\\", "/"),
            "shock_policy": str(SHOCK.relative_to(ROOT)).replace("\\", "/"),
            "morning_brief": str(BRIEF.relative_to(ROOT)).replace("\\", "/"),
            "p1_advisory_wiring": str(P1_WIRING.relative_to(ROOT)).replace("\\", "/"),
        },
        "reproduce": "py scripts/run_telegram_daily_p0_preflight_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(OUT)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
