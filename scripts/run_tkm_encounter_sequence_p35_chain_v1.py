#!/usr/bin/env python3
"""TKM encounter_sequence P35: 3-lens conflict resolver chain [HYPO]."""

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
OUT = ROOT / "reports/tkm_encounter_sequence_p35_chain_v1_latest.json"


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
    ap.add_argument("--skip-p34-refresh", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_p34_refresh:
        steps.append(_run("p34_refresh", "run_tkm_encounter_sequence_p34_chain_v1.py", ["--skip-http", "--skip-p33-refresh"]))

    if not steps or all(s["ok"] for s in steps):
        steps.extend(
            [
                _run("conflict_resolver_apply", "apply_encounter_sequence_conflict_resolver_sidecar_v1.py"),
                _run("myeongni_lens_separation", "check_tkm_myeongni_sasang_lens_separation_v1.py"),
                _run("logos_lens_separation", "check_tkm_logos_sasang_lens_separation_v1.py"),
                _run("conflict_resolver_kpi", "build_tkm_encounter_sequence_conflict_resolver_kpi_v1.py"),
                _run("weekly_report", "build_encounter_sequence_weekly_report_v1.py"),
                _run("p35_gate", "build_tkm_encounter_sequence_p35_gate_v1.py"),
            ]
        )

    if all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                PY,
                "-m",
                "pytest",
                "tests/test_encounter_sequence_p35_v1.py",
                "tests/test_encounter_sequence_p34_v1.py",
                "-q",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:p35_suite",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "ok": proc.returncode == 0,
            }
        )

    gate_path = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p35_gate_v1_latest.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig")) if gate_path.is_file() else {}
    doc = {
        "schema": "tkm_encounter_sequence_p35_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p35_gate_ok": gate.get("gate_ok"),
        "tkm_encounter_sequence_p35_status": gate.get("tkm_encounter_sequence_p35_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_tkm_encounter_sequence_p35_chain_v1.py --skip-http",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "status": doc.get("tkm_encounter_sequence_p35_status")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
