#!/usr/bin/env python3
"""TKM encounter_sequence passive weekly observation (L5/L6/L7 + Interpret) [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"
MYEONGNI_KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
LOGOS_KPI = ROOT / "reports/tkm_encounter_sequence_logos_kpi_v1_latest.json"
CROSS_KPI = ROOT / "reports/tkm_encounter_sequence_cross_lens_kpi_v1_latest.json"
INTERPRET = ROOT / "reports/myeongri_interpret_micro_retrain_chain_v1_latest.json"
SCHEDULER = ROOT / "docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _weekly_task_ready() -> bool:
    if SCHEDULER.is_file():
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
    myeongni = _load(MYEONGNI_KPI)
    logos = _load(LOGOS_KPI)
    cross = _load(CROSS_KPI)
    interpret = _load(INTERPRET)
    m_gold = myeongni.get("physician_gold_only") if isinstance(myeongni.get("physician_gold_only"), dict) else {}
    task_ready = _weekly_task_ready()
    interpret_cpu_ok = interpret.get("cpu_guard_ok") is True or not INTERPRET.is_file()
    l5_headline_ok = (
        myeongni.get("physician_gold_engine_ok") is True
        and int(m_gold.get("stub_report_linked_count") or 0) == 0
    )
    l6_headline_ok = logos.get("physician_gold_logos_ok") is True
    l7_headline_ok = cross.get("kpi_ok") is True and cross.get("motif_skew_gate_ok") is True
    observation_ok = (
        l5_headline_ok
        and l6_headline_ok
        and l7_headline_ok
        and interpret_cpu_ok
    )
    return {
        "schema": "tkm_encounter_sequence_passive_observation_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "non_gating": True,
        "observation_ok": observation_ok,
        "weekly_task_ready": task_ready,
        "interpret_cpu_guard_ok": interpret_cpu_ok,
        "interpret_gpu_train_attempted": interpret.get("gpu_train_attempted"),
        "interpret_gpu_train_ok": interpret.get("gpu_train_ok"),
        "cross_lens_resonance_index": cross.get("cross_lens_resonance_index"),
        "motif_top1_share": cross.get("motif_top1_share"),
        "motif_skew_gate_ok": cross.get("motif_skew_gate_ok"),
        "l5_myeongni_headline_ok": l5_headline_ok,
        "l6_logos_headline_ok": l6_headline_ok,
        "l7_cross_lens_headline_ok": l7_headline_ok,
        "note_ko": "패시브 관측 [HYPO][NON_GATING]; Track A·실매매·자동 트리거 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_passive_observation_v1.py",
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
