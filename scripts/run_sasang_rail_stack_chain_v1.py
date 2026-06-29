#!/usr/bin/env python3
"""Sasang rail full stack: containment → P2 enrichment → P3 ablation/literature [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_stack_chain_v1_latest.json"

PHASE_CHAINS: list[tuple[str, str, list[str]]] = [
    ("containment", "run_sasang_rail_containment_chain_v1.py", ["--skip-pytest"]),
    ("p2_enrichment", "run_sasang_rail_p2_chain_v1.py", ["--skip-pytest", "--skip-mirror"]),
    (
        "p3_ablation_literature",
        "run_sasang_rail_p3_chain_v1.py",
        ["--require-prior-phases", "--skip-pytest"],
    ),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_chain(name: str, script: str, extra: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + extra
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "args": extra,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def _run_ps(name: str, script_rel: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    ps = ROOT / script_rel
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "name": name,
        "script": script_rel,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-mirror", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for name, script, extra in PHASE_CHAINS:
        steps.append(_run_chain(name, script, extra))
        if not steps[-1]["ok"]:
            break

    if steps and all(s["ok"] for s in steps):
        if not args.skip_mirror:
            steps.append(_run_ps("pr_mirror_sync", "scripts/Sync-PrSasangPromotionMirror_v1.ps1"))
        steps.append(_run_chain("stack_gate", "build_sasang_rail_stack_gate_v1.py", []))

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in (
            "tests/test_sasang_rail_containment_v1.py",
            "tests/test_sasang_rail_p2_v1.py",
            "tests/test_sasang_rail_p3_v1.py",
            "tests/test_sasang_rail_stack_v1.py",
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

    stack_gate_path = ROOT / "docs/final/artifacts/sasang_rail_stack_gate_v1_latest.json"
    unified_path = ROOT / "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"
    stack_gate = _load_json(stack_gate_path)
    unified = _load_json(unified_path)

    doc = {
        "schema": "sasang_rail_stack_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "stack_gate_ok": stack_gate.get("gate_ok"),
        "unified_gate_ok": unified.get("gate_ok"),
        "sasang_rail_stack_status": stack_gate.get("sasang_rail_stack_status") or unified.get("sasang_rail_stack_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_stack_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["all_ok"], "sasang_rail_stack_status": doc.get("sasang_rail_stack_status")},
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    raise SystemExit(main())
