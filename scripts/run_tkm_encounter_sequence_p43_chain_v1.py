#!/usr/bin/env python3
"""TKM encounter_sequence P43: GPU+passive+curated observability chain [HYPO]."""

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
OUT = ROOT / "reports/tkm_encounter_sequence_p43_chain_v1_latest.json"


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
    ap.add_argument("--skip-p42-refresh", action="store_true")
    ap.add_argument("--with-gpu-interpret-train", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_p42_refresh:
        extra = ["--skip-http", "--skip-p41-refresh"]
        if args.with_gpu_interpret_train:
            extra.append("--with-gpu-interpret-train")
        steps.append(_run("p42_refresh", "run_tkm_encounter_sequence_p42_chain_v1.py", extra))

    if not steps or all(s["ok"] for s in steps):
        interpret_extra: list[str] = []
        if args.with_gpu_interpret_train and args.skip_p42_refresh:
            interpret_extra.append("--with-gpu-train")
        if interpret_extra:
            steps.append(_run("interpret_micro", "run_myeongri_interpret_micro_retrain_chain_v1.py", interpret_extra))
        else:
            steps.append(_run("interpret_cpu_guard", "run_myeongri_interpret_micro_retrain_chain_v1.py"))
        steps.extend(
            [
                _run("passive_observation", "build_tkm_encounter_sequence_passive_observation_v1.py"),
                _run("curated_review_mark", "run_encounter_sequence_curated_review_mark_v1.py"),
                _run("p43_observability_rollup", "build_tkm_encounter_sequence_p43_observability_rollup_v1.py"),
                _run("weekly_report", "build_encounter_sequence_weekly_report_v1.py"),
                _run("p43_gate", "build_tkm_encounter_sequence_p43_gate_v1.py"),
                _run("ops_closure", "build_tkm_encounter_sequence_ops_closure_v1.py"),
            ]
        )

    if all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                PY,
                "-m",
                "pytest",
                "tests/test_encounter_sequence_p43_v1.py",
                "tests/test_encounter_sequence_p42_v1.py",
                "-q",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:p43_suite",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "ok": proc.returncode == 0,
            }
        )

    gate_path = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p43_gate_v1_latest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig")) if gate_path.is_file() else {}
    doc = {
        "schema": "tkm_encounter_sequence_p43_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "research_only": True,
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p43_gate_ok": gate.get("gate_ok"),
        "tkm_encounter_sequence_p43_status": gate.get("tkm_encounter_sequence_p43_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_tkm_encounter_sequence_p43_chain_v1.py --skip-http",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "status": doc.get("tkm_encounter_sequence_p43_status")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
