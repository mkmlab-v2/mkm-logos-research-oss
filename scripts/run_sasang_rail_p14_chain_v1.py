#!/usr/bin/env python3
"""Sasang rail P14: prune mainline + attested eval gate + drift alert [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_p14_chain_v1_latest.json"


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
    ap.add_argument("--with-p13-refresh", action="store_true", help="Run full P13 refresh before P14 steps")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if args.with_p13_refresh:
        steps.append(
            _run(
                "p13_refresh",
                "run_sasang_rail_p13_chain_v1.py",
                ["--skip-pytest", "--skip-p12-refresh"],
            )
        )

    if not steps or all(s["ok"] for s in steps):
        steps.append(_run("dummy_archive_export", "export_sasang_joint_benchmark_dummy_archive_v1.py"))
        steps.append(_run("attested_snapshot", "build_sasang_joint_benchmark_attested_only_snapshot_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("mainline_prune", "prune_sasang_joint_benchmark_dummy_from_mainline_v1.py", ["--apply"]))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("benchmark_validate", "validate_sasang_saju_joint_benchmark_jsonl_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("dual_probe_ablation", "run_sasang_4agent_dual_probe_ablation_v1.py"))
        steps.append(_run("dual_probe_drift", "build_sasang_4agent_dual_probe_drift_report_v1.py"))
        steps.append(_run("weekly_drift_alert", "build_sasang_4agent_dual_probe_weekly_drift_alert_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("clinical_template_gate", "build_sasang_commander_attested_clinical_template_gate_v1.py"))
        steps.append(_run("attested_classification_gate", "build_sasang_attested_only_classification_gate_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("benchmark_composition", "build_sasang_joint_benchmark_composition_report_v1.py"))
        steps.append(_run("dummy_rebalance", "build_sasang_joint_benchmark_dummy_rebalance_report_v1.py"))
        steps.append(_run("tier_partition", "build_sasang_joint_benchmark_tier_partition_report_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("p14_gate", "build_sasang_rail_p14_gate_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("master_gate_p14", "build_sasang_rail_master_gate_v1.py"))

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [PY, "-m", "pytest", "tests/test_sasang_rail_p14_v1.py", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:tests/test_sasang_rail_p14_v1.py",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-250:],
                "ok": proc.returncode == 0,
            }
        )

    p14_path = ROOT / "docs/final/artifacts/sasang_rail_p14_gate_v1_latest.json"
    p14 = json.loads(p14_path.read_text(encoding="utf-8-sig")) if p14_path.is_file() else {}
    master_path = ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
    master = json.loads(master_path.read_text(encoding="utf-8-sig")) if master_path.is_file() else {}

    doc = {
        "schema": "sasang_rail_p14_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p14_gate_ok": p14.get("gate_ok"),
        "sasang_rail_p14_status": p14.get("sasang_rail_p14_status"),
        "master_gate_ok": master.get("gate_ok"),
        "sasang_rail_master_status": master.get("sasang_rail_master_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_p14_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["all_ok"],
                "sasang_rail_p14_status": doc.get("sasang_rail_p14_status"),
                "master_status": doc.get("sasang_rail_master_status"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
