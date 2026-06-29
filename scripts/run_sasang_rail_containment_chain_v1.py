#!/usr/bin/env python3
"""Sasang rail: independent lens → market overlay → containment RAG → gate [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_containment_chain_v1_latest.json"

STEPS = [
    ("independent_lens", "run_lens_sasang.py"),
    ("market_lens", "run_market_sasang_lens_v1.py"),
    ("rag_excerpt", "build_notebooklm_lens_sasang_rag_excerpt_v1.py"),
    ("observation_report", "build_sasang_lens_observation_report_v1.py"),
    ("containment_gate", "build_sasang_rail_containment_gate_v1.py"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run([PY, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-300:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for name, script in STEPS:
        steps.append(_run(name, script))
        if not steps[-1]["ok"]:
            break

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in (
            "tests/test_sasang_rail_containment_v1.py",
            "tests/test_mkm_ltm_bench_route_purity_v1.py",
            "tests/test_build_notebooklm_lens_sasang_rag_excerpt_v1.py",
        ):
            t0 = time.perf_counter()
            proc = subprocess.run([PY, "-m", "pytest", test_path, "-q"], cwd=ROOT, capture_output=True, text=True)
            steps.append(
                {
                    "name": f"pytest:{test_path}",
                    "exit_code": proc.returncode,
                    "elapsed_sec": round(time.perf_counter() - t0, 2),
                    "stdout_tail": (proc.stdout or "")[-200:],
                    "ok": proc.returncode == 0,
                }
            )
            if proc.returncode != 0:
                break

    gate_path = ROOT / "docs/final/artifacts/sasang_rail_containment_gate_v1_latest.json"
    gate = {}
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "sasang_rail_containment_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "containment_gate_ok": gate.get("gate_ok"),
        "sasang_rail_status": gate.get("sasang_rail_status"),
        "reproduce": "py scripts/run_sasang_rail_containment_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["all_ok"], "sasang_rail_status": doc.get("sasang_rail_status")},
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
