#!/usr/bin/env python3
"""Sasang rail P15: eval path lock + archive snapshot + drift webhook stub [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_p15_chain_v1_latest.json"


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
    ap.add_argument("--with-p14-refresh", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if args.with_p14_refresh:
        steps.append(_run("p14_refresh", "run_sasang_rail_p14_chain_v1.py", ["--skip-pytest"]))

    if not steps or all(s["ok"] for s in steps):
        steps.append(_run("dummy_archive_rebuild", "rebuild_sasang_dummy_archive_from_sources_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("weekly_drift_alert", "build_sasang_4agent_dual_probe_weekly_drift_alert_v1.py"))
        steps.append(_run("drift_webhook_stub", "build_sasang_4agent_dual_probe_drift_webhook_stub_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("attested_eval_chain", "run_sasang_attested_only_eval_chain_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("clinical_pending_gate", "build_sasang_commander_clinical_pending_gate_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("p15_gate", "build_sasang_rail_p15_gate_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("master_gate_p15", "build_sasang_rail_master_gate_v1.py"))

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [PY, "-m", "pytest", "tests/test_sasang_rail_p15_v1.py", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:tests/test_sasang_rail_p15_v1.py",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-250:],
                "ok": proc.returncode == 0,
            }
        )

    p15_path = ROOT / "docs/final/artifacts/sasang_rail_p15_gate_v1_latest.json"
    p15 = json.loads(p15_path.read_text(encoding="utf-8-sig")) if p15_path.is_file() else {}
    master_path = ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
    master = json.loads(master_path.read_text(encoding="utf-8-sig")) if master_path.is_file() else {}

    doc = {
        "schema": "sasang_rail_p15_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p15_gate_ok": p15.get("gate_ok"),
        "sasang_rail_p15_status": p15.get("sasang_rail_p15_status"),
        "master_gate_ok": master.get("gate_ok"),
        "sasang_rail_master_status": master.get("sasang_rail_master_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_p15_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["all_ok"],
                "sasang_rail_p15_status": doc.get("sasang_rail_p15_status"),
                "master_status": doc.get("sasang_rail_master_status"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
