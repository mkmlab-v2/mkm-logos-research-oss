#!/usr/bin/env python3
"""Oracle module vs HD-AE weekly scheduler coexistence report (read-only).

  py scripts/build_mkm_oracle_module_scheduler_coexistence_v1.py
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
OUT = ROOT / "reports/mkm_oracle_module_scheduler_coexistence_v1_latest.json"

TASKS = (
    {
        "task_name": "MKM_HdAutonomousEvolution_Weekly",
        "default_sunday_local": "09:15",
        "lane_owner": "hd_autonomous_evolution",
        "forbidden_overlap_with": "bloom_cap_bump",
    },
    {
        "task_name": "MKM_Oracle_Module_Observability_Weekly",
        "default_sunday_local": "09:45",
        "lane_owner": "oracle_module_observability",
        "forbidden_overlap_with": "mkmlife_deploy",
    },
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _task_state(name: str) -> dict[str, Any]:
    proc = subprocess.run(
        ["schtasks", "/Query", "/TN", name, "/FO", "LIST", "/V"],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return {"exists": False, "state": None, "schedule_type": None, "start_time": None}
    text = proc.stdout or ""
    state = None
    schedule = None
    start = None
    for line in text.splitlines():
        low = line.lower()
        if low.startswith("status:"):
            state = line.split(":", 1)[1].strip()
        elif low.startswith("schedule type:"):
            schedule = line.split(":", 1)[1].strip()
        elif low.startswith("start time:"):
            start = line.split(":", 1)[1].strip()
    return {
        "exists": True,
        "state": state,
        "schedule_type": schedule,
        "start_time": start,
    }


def build_report(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for spec in TASKS:
        live = _task_state(spec["task_name"])
        rows.append({**spec, **live})

    defaults = [r["default_sunday_local"] for r in rows]
    coexistence_ok = len(set(defaults)) == len(defaults) and all(
        r.get("exists") for r in rows
    )

    return {
        "schema": "mkm_oracle_module_scheduler_coexistence_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "coexistence_ok": coexistence_ok,
        "default_stagger_minutes": 30,
        "partition_note_ko": (
            "HD-AE 09:15 = intel/swarm/hybrid · Module 09:45 = observability/resume — "
            "cap bump 금지 · 동시 실행 회피"
        ),
        "tasks": rows,
        "ssot_tier4": "docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json",
        "repro": "py scripts/build_mkm_oracle_module_scheduler_coexistence_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build_report(args.workspace_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"coexistence_ok": doc["coexistence_ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if doc["coexistence_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
