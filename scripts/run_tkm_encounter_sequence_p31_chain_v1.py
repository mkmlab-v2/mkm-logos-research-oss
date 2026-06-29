#!/usr/bin/env python3
"""TKM encounter_sequence P31: ledger stub backfill + engine stub-free gate [HYPO]."""

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
OUT = ROOT / "reports/tkm_encounter_sequence_p31_chain_v1_latest.json"


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-http", action="store_true")
    ap.add_argument("--skip-interpret", action="store_true")
    ap.add_argument("--with-gpu-interpret-train", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = [
        _run("engine_materialize", "materialize_tkm_physician_gold_myeongni_engine_v1.py"),
        _run("ledger_backfill", "backfill_tkm_myeongni_engine_from_ledger_v1.py"),
        _run("myeongni_cross_refresh", "refresh_encounter_sequence_myeongni_cross_check_v1.py"),
        _run("myeongni_kpi", "build_tkm_encounter_sequence_myeongni_kpi_v1.py"),
        _run("weekly_report", "build_encounter_sequence_weekly_report_v1.py"),
        _run("passive_observation", "build_tkm_myeongni_passive_observation_v1.py"),
    ]

    if not args.skip_interpret and all(s["ok"] for s in steps):
        interpret_extra: list[str] = []
        if args.with_gpu_interpret_train:
            interpret_extra.append("--with-gpu-train")
        steps.append(_run("interpret_micro", "run_myeongri_interpret_micro_retrain_chain_v1.py", interpret_extra))

    if all(s["ok"] for s in steps):
        steps.append(_run("p30_gate", "build_tkm_encounter_sequence_p30_gate_v1.py"))
        steps.append(_run("p31_gate", "build_tkm_encounter_sequence_p31_gate_v1.py"))

    if all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                PY,
                "-m",
                "pytest",
                "tests/test_encounter_sequence_p31_v1.py",
                "tests/test_encounter_sequence_p30_v1.py",
                "tests/test_tkm_physician_gold_myeongni_engine_v1.py",
                "tests/test_encounter_sequence_weekly_report_v1.py",
                "-q",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:p31_suite",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "ok": proc.returncode == 0,
            }
        )

    gate_path = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p31_gate_v1_latest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig")) if gate_path.is_file() else {}

    doc = {
        "schema": "tkm_encounter_sequence_p31_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p31_gate_ok": gate.get("gate_ok"),
        "tkm_encounter_sequence_p31_status": gate.get("tkm_encounter_sequence_p31_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_tkm_encounter_sequence_p31_chain_v1.py --skip-http",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "status": doc.get("tkm_encounter_sequence_p31_status")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
