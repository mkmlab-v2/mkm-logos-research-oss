#!/usr/bin/env python3
"""TKM 명리 passive weekly observation rollup [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_myeongni_passive_observation_v1_latest.json"
MYEONGNI_KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
SCHEDULER = ROOT / "docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _weekly_task_ready() -> bool:
    if not SCHEDULER.is_file():
        return False
    doc = _load(SCHEDULER)
    tasks = doc.get("tasks") if isinstance(doc.get("tasks"), list) else []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        name = str(task.get("name") or task.get("task_name") or "")
        if "TkmEncounterSequence" in name or "TKM-TkmEncounterSequence" in name:
            return task.get("ready") is True or task.get("status") == "Ready"
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "(Get-ScheduledTask -TaskName 'MKM-TkmEncounterSequence-Weekly' -ErrorAction SilentlyContinue).State",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    state = (proc.stdout or "").strip()
    return state in ("Ready", "Running")


def build() -> dict[str, Any]:
    kpi = _load(MYEONGNI_KPI)
    weekly = _load(WEEKLY)
    l5 = weekly.get("l5_myeongni_kpi") if isinstance(weekly.get("l5_myeongni_kpi"), dict) else {}
    gold = kpi.get("physician_gold_only") if isinstance(kpi.get("physician_gold_only"), dict) else {}
    task_ready = _weekly_task_ready()
    observation_ok = (
        kpi.get("kpi_ok") is True
        and l5.get("l5_myeongni_headline_ok") is True
        and int(gold.get("stub_report_linked_count") or 0) == 0
    )
    return {
        "schema": "tkm_myeongni_passive_observation_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "observation_ok": observation_ok,
        "weekly_task_ready": task_ready,
        "engine_report_linked_count": gold.get("engine_report_linked_count"),
        "engine_report_linked_rate": gold.get("engine_report_linked_rate"),
        "cross_check_computed_count": (kpi.get("all_ledger") or {}).get("cross_check_computed_count"),
        "l5_myeongni_headline_ok": l5.get("l5_myeongni_headline_ok"),
        "note_ko": "패시브 관측만; Track A·실매매·자동 트리거 금지.",
        "reproduce": "py scripts/build_tkm_myeongni_passive_observation_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("observation_ok"), "weekly_task_ready": doc.get("weekly_task_ready")}))
    return 0 if doc.get("observation_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
