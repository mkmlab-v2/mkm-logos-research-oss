#!/usr/bin/env python3
"""Sasang rail P9: literature supervised + curated apply + master refresh [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_p9_chain_v1_latest.json"


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
    ap.add_argument("--apply-promote", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for name, script in (
        ("literature_supervised", "run_sasang_literature_supervised_chain_v1.py"),
        ("benchmark_composition", "build_sasang_joint_benchmark_composition_report_v1.py"),
    ):
        steps.append(_run(name, script))
        if not steps[-1]["ok"]:
            break

    if steps and all(s["ok"] for s in steps):
        p6_extra = ["--skip-pytest"]
        if args.apply_promote:
            p6_extra.append("--apply-promote")
        steps.append(_run("p6_curated", "run_sasang_rail_p6_chain_v1.py", p6_extra))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("master_refresh", "run_sasang_rail_master_chain_v1.py", ["--skip-pytest", "--skip-stack"]))

    if steps and all(s["ok"] for s in steps):
        steps.append(_run("p9_gate", "build_sasang_rail_p9_gate_v1.py"))

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in (
            "tests/test_export_sasang_literature_supervised_jsonl_v1.py",
            "tests/test_sasang_rail_p9_v1.py",
        ):
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

    p9_path = ROOT / "docs/final/artifacts/sasang_rail_p9_gate_v1_latest.json"
    p9 = json.loads(p9_path.read_text(encoding="utf-8-sig")) if p9_path.is_file() else {}

    doc = {
        "schema": "sasang_rail_p9_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p9_gate_ok": p9.get("gate_ok"),
        "sasang_rail_p9_status": p9.get("sasang_rail_p9_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_p9_chain_v1.py --apply-promote",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["all_ok"], "sasang_rail_p9_status": doc.get("sasang_rail_p9_status")},
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
