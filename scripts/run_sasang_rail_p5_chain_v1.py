#!/usr/bin/env python3
"""Sasang rail P5: review queue, curated promote gate, full ablation, stack refresh [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_p5_chain_v1_latest.json"

STEPS: list[tuple[str, str] | tuple[str, str, list[str]]] = [
    ("review_queue_from_catalog", "build_sasang_saju_joint_review_queue_from_catalog_v1.py"),
    ("auto_enrich_stub", "auto_enrich_sasang_from_literature_stub_v1.py"),
    ("literature_curated_promote_gate", "build_sasang_literature_curated_promote_gate_v1.py"),
    (
        "ablation_full_bootstrap",
        "run_sasang_4agent_protocol_ablation_v1.py",
        ["--bootstrap-trials", "200"],
    ),
    ("literature_majority_resolve", "resolve_literature_sasang_majority_v1.py"),
    ("literature_supervised_refresh", "run_sasang_literature_supervised_chain_v1.py"),
    ("joint_benchmark_validate", "validate_sasang_saju_joint_benchmark_jsonl_v1.py"),
    ("joint_benchmark_smoke", "run_sasang_saju_joint_benchmark_smoke_v1.py"),
    ("p3_gate_refresh", "build_sasang_rail_p3_gate_v1.py"),
    ("unified_gate_refresh", "build_sasang_rail_unified_gate_v1.py"),
    ("stack_gate_refresh", "build_sasang_rail_stack_gate_v1.py"),
    ("p5_gate", "build_sasang_rail_p5_gate_v1.py"),
]


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
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def _run_chain(name: str, script: str, extra: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + extra
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-stack-chain", action="store_true")
    ap.add_argument("--apply-promote", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for item in STEPS:
        if item[0] == "literature_curated_promote_gate" and args.apply_promote:
            steps.append(_run(item[0], item[1], ["--apply"]))
        elif len(item) == 3:
            steps.append(_run(item[0], item[1], item[2]))
        else:
            steps.append(_run(item[0], item[1]))
        if not steps[-1]["ok"]:
            break

    if steps and all(s["ok"] for s in steps) and not args.skip_stack_chain:
        steps.append(
            _run_chain(
                "stack_chain_refresh",
                "run_sasang_rail_stack_chain_v1.py",
                ["--skip-pytest"],
            )
        )

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in (
            "tests/test_build_sasang_literature_curated_promote_gate_v1.py",
            "tests/test_sasang_rail_p5_v1.py",
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

    p5_path = ROOT / "docs/final/artifacts/sasang_rail_p5_gate_v1_latest.json"
    p5 = json.loads(p5_path.read_text(encoding="utf-8-sig")) if p5_path.is_file() else {}

    doc = {
        "schema": "sasang_rail_p5_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p5_gate_ok": p5.get("gate_ok"),
        "sasang_rail_p5_status": p5.get("sasang_rail_p5_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_p5_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["all_ok"], "sasang_rail_p5_status": doc.get("sasang_rail_p5_status")},
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
