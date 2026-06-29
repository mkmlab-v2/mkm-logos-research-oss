#!/usr/bin/env python3
"""TKM encounter_sequence P19: clinic bridge + unified KPI + weekly register [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/tkm_encounter_sequence_p19_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str, extra: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "ok": proc.returncode == 0,
    }


def _run_ps(name: str, script: str, extra: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / script)] + (
        extra or []
    )
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-weekly-register", action="store_true")
    ap.add_argument("--with-p18-refresh", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if args.with_p18_refresh:
        steps.append(_run("p18_refresh", "run_tkm_encounter_sequence_p18_chain_v1.py", ["--skip-pytest"]))

    if not steps or all(s["ok"] for s in steps):
        steps.append(_run("dummy_autofill", "bootstrap_tkm_encounter_sequence_dummy_autofill_v1.py"))

    if not steps or all(s["ok"] for s in steps):
        steps.append(_run("build_clinic_summary", "build_clinic_mvp_disagreement_summary_v1.py"))
        steps.append(_run("build_encounter_summary", "build_encounter_sequence_summary_v1.py"))
        steps.append(_run("unified_summary", "build_tkm_clinic_encounter_unified_disagreement_summary_v1.py"))
        steps.append(_run("curated_learning_draft", "build_encounter_sequence_curated_learning_draft_v1.py"))
        steps.append(
            _run(
                "curated_learning_apply",
                "apply_encounter_sequence_curated_learning_v1.py",
                ["--dummy-auto-fill"],
            )
        )
        steps.append(_run("weekly_report", "build_encounter_sequence_weekly_report_v1.py"))
        steps.append(_run("intake_fusion_l0_smoke", "run_intake_fusion_encounter_sequence_smoke_v1.py"))

    if steps and all(s["ok"] for s in steps) and not args.skip_weekly_register:
        steps.append(_run_ps("register_weekly_task", "Register-TkmEncounterSequenceWeeklyReport_v1.ps1"))
        steps.append(_run("verify_weekly_task", "verify_tkm_encounter_sequence_weekly_task_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("p19_gate", "build_tkm_encounter_sequence_p19_gate_v1.py"))

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                PY,
                "-m",
                "pytest",
                "tests/test_convert_clinic_capture_to_encounter_sequence_v1.py",
                "tests/test_encounter_sequence_p19_v1.py",
                "-q",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:p19_suite",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "ok": proc.returncode == 0,
            }
        )

    gate_path = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p19_gate_v1_latest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig")) if gate_path.is_file() else {}

    doc = {
        "schema": "tkm_encounter_sequence_p19_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p19_gate_ok": gate.get("gate_ok"),
        "tkm_encounter_sequence_p19_status": gate.get("tkm_encounter_sequence_p19_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_tkm_encounter_sequence_p19_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "status": doc.get("tkm_encounter_sequence_p19_status")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
