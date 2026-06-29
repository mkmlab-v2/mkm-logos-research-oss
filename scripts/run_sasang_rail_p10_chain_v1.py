#!/usr/bin/env python3
"""Sasang rail P10: P9 refresh + 4-agent real-slice + non-dummy classification [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_p10_chain_v1_latest.json"
REAL_SLICE_OUT = ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_real_slice_latest.json"


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
    ap.add_argument("--skip-p9-refresh", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_p9_refresh:
        steps.append(_run("p9_refresh", "run_sasang_rail_p9_chain_v1.py", ["--skip-pytest"]))

    if not steps or all(s["ok"] for s in steps):
        t0 = time.perf_counter()
        cmd = [
            PY,
            str(ROOT / "scripts/run_sasang_4agent_collision_btrack_protocol_v1.py"),
            "--use-real-slice",
            "--out-json",
            str(REAL_SLICE_OUT),
            "--bootstrap-trials",
            "200",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        steps.append(
            {
                "name": "protocol_4agent_real_slice",
                "script": "run_sasang_4agent_collision_btrack_protocol_v1.py",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-400:],
                "ok": proc.returncode == 0,
            }
        )

    if steps and all(s["ok"] for s in steps):
        steps.append(
            _run(
                "non_dummy_classification",
                "build_sasang_joint_benchmark_non_dummy_classification_smoke_v1.py",
            )
        )

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("p10_gate", "build_sasang_rail_p10_gate_v1.py"))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("master_gate_p10", "build_sasang_rail_master_gate_v1.py"))

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in ("tests/test_sasang_rail_p10_v1.py",):
            t0 = time.perf_counter()
            proc = subprocess.run([PY, "-m", "pytest", test_path, "-q"], cwd=ROOT, capture_output=True, text=True)
            steps.append(
                {
                    "name": f"pytest:{test_path}",
                    "exit_code": proc.returncode,
                    "elapsed_sec": round(time.perf_counter() - t0, 2),
                    "stdout_tail": (proc.stdout or "")[-250:],
                    "ok": proc.returncode == 0,
                }
            )
            if proc.returncode != 0:
                break

    p10_path = ROOT / "docs/final/artifacts/sasang_rail_p10_gate_v1_latest.json"
    p10 = json.loads(p10_path.read_text(encoding="utf-8-sig")) if p10_path.is_file() else {}
    master_path = ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
    master = json.loads(master_path.read_text(encoding="utf-8-sig")) if master_path.is_file() else {}

    doc = {
        "schema": "sasang_rail_p10_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p10_gate_ok": p10.get("gate_ok"),
        "sasang_rail_p10_status": p10.get("sasang_rail_p10_status"),
        "master_gate_ok": master.get("gate_ok"),
        "sasang_rail_master_status": master.get("sasang_rail_master_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_p10_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["all_ok"],
                "sasang_rail_p10_status": doc.get("sasang_rail_p10_status"),
                "master_status": doc.get("sasang_rail_master_status"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
