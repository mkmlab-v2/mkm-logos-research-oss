#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "inspector_daily_report_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _task_status(task_name: str) -> dict[str, Any]:
    ps = (
        f"$i=Get-ScheduledTaskInfo -TaskName '{task_name}' -ErrorAction SilentlyContinue; "
        "if($i){"
        "Write-Output ($i.LastTaskResult);"
        "} else { Write-Output 'MISSING' }"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    val = (proc.stdout or "").strip()
    if val == "MISSING" or not val:
        return {"task_name": task_name, "state": "unknown", "last_task_result": None}
    try:
        code = int(val)
    except ValueError:
        return {"task_name": task_name, "state": "unknown", "last_task_result": None}
    return {
        "task_name": task_name,
        "state": "ok" if code == 0 else "fail",
        "last_task_result": code,
    }


def _domain_status(runtime_ok: bool, cost_ok: bool, security_ok: bool, quality_ok: bool) -> tuple[str, int]:
    score = 100
    if not runtime_ok:
        score -= 25
    if not cost_ok:
        score -= 20
    if not security_ok:
        score -= 30
    if not quality_ok:
        score -= 15
    if score >= 80:
        return "GREEN", score
    if score >= 60:
        return "YELLOW", score
    return "RED", score


def main() -> int:
    c2 = _read_json(ART / "c2_aegis_guardrail_status_latest.json")
    cost = _read_json(ART / "cost_watch_monitor_latest.json")
    go = _read_json(ART / "a_track_go_nogo_status_latest.json")

    t_daily = _task_status("GeneralProphecyDailyQueueV1")
    t_vibe = _task_status("VibeDailyProphecyEvolutionLoop")

    runtime_ok = all(
        x.get("state") == "ok"
        for x in (t_daily, t_vibe)
        if x.get("last_task_result") is not None
    )
    cost_ok = bool(cost) and str((cost.get("billing") or {}).get("status") or "") == "ok"
    security_ok = str(c2.get("status") or "").startswith("GREEN")
    quality_ok = str((go.get("result") or {}).get("overall_go_no_go") or "") == "GO"

    overall, score = _domain_status(runtime_ok, cost_ok, security_ok, quality_ok)

    # NON_GATING affect layer: used to shape wording and proposals only (never triggers actions).
    calm = 0.7 if runtime_ok and security_ok else 0.4
    urgency = 0.2 if runtime_ok else 0.6
    fatigue = 0.3
    confidence = 0.7 if overall == "GREEN" else 0.5
    tone = "Keep it concise; focus on highest-signal changes only."
    opx = "Low friction expected; monitor quietly unless failures repeat."
    style = "summary_first"
    report: dict[str, Any] = {
        "schema": "inspector_daily_report_v1",
        "schema_version": "1.0.0",
        "ts_utc": _now_iso(),
        "fact_lock": {
            "constitution_ref": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
            "mode": "observation_only_2weeks",
        },
        "system_posture": {"overall": overall, "score_0_100": score},
        "affect_layer": {
            "non_gating": True,
            "mood_vector": {"calm": calm, "urgency": urgency, "fatigue": fatigue, "confidence": confidence},
            "tone_suggestion": tone,
            "operator_experience": opx,
            "recommendation_style": style,
        },
        "human_feedback_slot": {
            "enabled": True,
            "prompt": "Was this report helpful? (e.g. ok / too noisy / missed X / great).",
            "response": "",
        },
        "domains": {
            "runtime_health": {"status": "GREEN" if runtime_ok else "YELLOW", "signals": [t_daily, t_vibe]},
            "cost_governance": {
                "status": "GREEN" if cost_ok else "YELLOW",
                "signals": [{"billing_status": (cost.get("billing") or {}).get("status")}],
            },
            "security_ip": {
                "status": "GREEN" if security_ok else "YELLOW",
                "signals": [{"c2_aegis_status": c2.get("status")}],
            },
            "code_quality_env": {
                "status": "GREEN" if quality_ok else "YELLOW",
                "signals": [{"a_track_go_no_go": (go.get("result") or {}).get("overall_go_no_go")}],
            },
        },
        "source_evidence": {
            "c2_aegis": "docs/final/artifacts/c2_aegis_guardrail_status_latest.json",
            "cost_watch": "docs/final/artifacts/cost_watch_monitor_latest.json",
            "a_track_go_nogo": "docs/final/artifacts/a_track_go_nogo_status_latest.json",
        },
        "actions_proposed": [],
        "audit": {"run_id": str(uuid.uuid4()), "agent": "MKM_Internal_Inspector_v1", "publish_scope": "local_only"},
    }

    if not runtime_ok:
        report["actions_proposed"].append(
            {
                "action_id": "act-runtime-retry-001",
                "level": "L1",
                "owner": "Operator",
                "description": "retry failed scheduled task once",
                "requires_commander_approval": False,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {OUT}")
    print(f"overall: {overall} score={score}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

