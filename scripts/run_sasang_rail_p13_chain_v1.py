#!/usr/bin/env python3
"""Sasang rail P13: archive + attested snapshot + dual drift ablation [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_p13_chain_v1_latest.json"
ATTESTED_SNAPSHOT = ROOT / "data/myeongni/sasang_saju_joint_benchmark_attested_only_v1.jsonl"


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
    ap.add_argument("--skip-p12-refresh", action="store_true")
    ap.add_argument("--apply-promote", action="store_true")
    ap.add_argument("--seed-drift-baseline", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_p12_refresh:
        steps.append(
            _run(
                "p12_refresh",
                "run_sasang_rail_p12_chain_v1.py",
                ["--skip-pytest", "--skip-p11-refresh"],
            )
        )

    if not steps or all(s["ok"] for s in steps):
        steps.append(_run("kospi_proxy_csv", "build_sasang_kospi_proxy_timeseries_from_backtest_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("dual_probe_ablation", "run_sasang_4agent_dual_probe_ablation_v1.py"))

    if steps and all(s["ok"] for s in steps):
        drift_extra = ["--seed-baseline"] if args.seed_drift_baseline else []
        steps.append(_run("dual_probe_drift", "build_sasang_4agent_dual_probe_drift_report_v1.py", drift_extra))

    if steps and all(s["ok"] for s in steps):
        p6_extra = ["--skip-pytest"]
        if args.apply_promote:
            p6_extra.append("--apply-promote")
        steps.append(_run("p6_curated", "run_sasang_rail_p6_chain_v1.py", p6_extra))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("dummy_archive_export", "export_sasang_joint_benchmark_dummy_archive_v1.py"))
        steps.append(_run("attested_snapshot", "build_sasang_joint_benchmark_attested_only_snapshot_v1.py"))
        steps.append(_run("tier_partition", "build_sasang_joint_benchmark_tier_partition_report_v1.py"))
        steps.append(
            _run(
                "attested_classification",
                "build_sasang_joint_benchmark_non_dummy_classification_smoke_v1.py",
                ["--dataset", str(ATTESTED_SNAPSHOT)],
            )
        )

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("p13_gate", "build_sasang_rail_p13_gate_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("master_gate_p13", "build_sasang_rail_master_gate_v1.py"))

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [PY, "-m", "pytest", "tests/test_sasang_rail_p13_v1.py", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:tests/test_sasang_rail_p13_v1.py",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-250:],
                "ok": proc.returncode == 0,
            }
        )

    p13_path = ROOT / "docs/final/artifacts/sasang_rail_p13_gate_v1_latest.json"
    p13 = json.loads(p13_path.read_text(encoding="utf-8-sig")) if p13_path.is_file() else {}
    master_path = ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
    master = json.loads(master_path.read_text(encoding="utf-8-sig")) if master_path.is_file() else {}

    doc = {
        "schema": "sasang_rail_p13_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p13_gate_ok": p13.get("gate_ok"),
        "sasang_rail_p13_status": p13.get("sasang_rail_p13_status"),
        "master_gate_ok": master.get("gate_ok"),
        "sasang_rail_master_status": master.get("sasang_rail_master_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_p13_chain_v1.py --apply-promote --seed-drift-baseline",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["all_ok"],
                "sasang_rail_p13_status": doc.get("sasang_rail_p13_status"),
                "master_status": doc.get("sasang_rail_master_status"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
