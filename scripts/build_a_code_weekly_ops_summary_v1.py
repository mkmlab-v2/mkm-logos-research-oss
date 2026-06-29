#!/usr/bin/env python3
"""One-page A-code weekly full vs light ops summary ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIGHT = ROOT / "docs/final/artifacts/a_code_light_ops_profile_v1_latest.json"
DEFAULT_WEEKLY = ROOT / "reports/a_code_operator_assist_lane_weekly_tasks_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/a_code_weekly_ops_summary_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/a_code_weekly_ops_summary_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_summary() -> dict[str, Any]:
    light = _read(DEFAULT_LIGHT)
    weekly = _read(DEFAULT_WEEKLY)
    profiles = weekly.get("profiles") or []

    full = next((p for p in profiles if not p.get("SkipGovernorBundle")), None)
    lite = next((p for p in profiles if p.get("SkipGovernorBundle")), None)

    return {
        "schema": "a_code_weekly_ops_summary_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "profiles": {
            "daily_light": {
                "persona": light.get("daily_persona") or "OperatorAssistLane",
                "routine": light.get("routine_script"),
                "skip_governor_bundle": True,
                "use": "일상·hero evening·TG/dev pack thin",
            },
            "weekly_full": {
                "task_name": (full or {}).get("TaskName"),
                "run_at_local": (full or {}).get("RunAt"),
                "persona": "OperatorAssistLaneFull",
                "skip_governor_bundle": False,
                "use": "주간 multiday governor 포함 full refresh",
            },
            "weekly_light": {
                "task_name": (lite or {}).get("TaskName") or light.get("weekly_task_name"),
                "run_at_local": (lite or {}).get("RunAt") or light.get("weekly_run_at_local"),
                "persona": light.get("weekly_light_persona") or "OperatorAssistLaneLight",
                "skip_governor_bundle": True,
                "use": "주간 operator lane만 (governor multiday 생략)",
            },
        },
        "register": weekly.get("verify_command") or "Register-ACodeOperatorAssistLaneWeeklyTasks_v1.ps1",
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_auto_trigger": False,
            "non_gating": True,
        },
    }


def render_md(doc: dict[str, Any]) -> str:
    p = doc.get("profiles") or {}
    daily = p.get("daily_light") or {}
    full = p.get("weekly_full") or {}
    lite = p.get("weekly_light") or {}
    lines = [
        "# A-code weekly ops — full vs light (1-page)",
        "",
        f"- generated_at_utc: `{doc.get('generated_at_utc')}`",
        f"- research_only: `{doc.get('research_only')}` · non-gating `[HYPO]`",
        "",
        "## Daily / evening (light)",
        "",
        f"- Persona: `{daily.get('persona')}`",
        f"- Routine: `{daily.get('routine')}`",
        f"- Use: {daily.get('use')}",
        "",
        "## Weekly full (Sunday)",
        "",
        f"- Task: `{full.get('task_name')}` @ `{full.get('run_at_local')}`",
        f"- Persona: `{full.get('persona')}`",
        f"- Includes: multiday governor replay + promotion gate chain",
        "",
        "## Weekly light (Sunday)",
        "",
        f"- Task: `{lite.get('task_name')}` @ `{lite.get('run_at_local')}`",
        f"- Persona: `{lite.get('persona')}`",
        f"- Includes: operator lane only (`-SkipGovernorBundle`)",
        "",
        "## Track wall",
        "",
        "- Track A · live · MS paste 승격 **없음**",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    doc = build_summary()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(doc), encoding="utf-8")
    print(f"OK: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
