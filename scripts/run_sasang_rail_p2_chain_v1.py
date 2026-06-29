#!/usr/bin/env python3
"""Sasang rail P2: interpretive refresh, 4-agent smoke, literature joint bench, PR mirror [HYPO]."""

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
OUT = ROOT / "reports/sasang_rail_p2_chain_v1_latest.json"

STEPS: list[tuple[str, str] | tuple[str, str, list[str]]] = [
    ("interpretive_bundle", "build_sasang_interpretive_insight_bundle_v1.py"),
    ("rag_excerpt", "build_notebooklm_lens_sasang_rag_excerpt_v1.py"),
    ("nl_packs", "build_notebooklm_lens_source_packs_v1.py"),
    (
        "protocol_4agent_smoke",
        "run_sasang_4agent_collision_btrack_protocol_v1.py",
        ["--ticks", "400", "--bootstrap-trials", "100"],
    ),
    ("joint_benchmark_validate", "validate_sasang_saju_joint_benchmark_jsonl_v1.py"),
    ("joint_benchmark_smoke", "run_sasang_saju_joint_benchmark_smoke_v1.py"),
    ("p2_gate", "build_sasang_rail_p2_gate_v1.py"),
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


def _run_ps(name: str, script_rel: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    ps = ROOT / script_rel
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps),
        ],
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
    for item in STEPS:
        if len(item) == 3:
            name, script, extra = item
            steps.append(_run(name, script, extra))
        else:
            name, script = item  # type: ignore[misc]
            steps.append(_run(name, script))
        if not steps[-1]["ok"]:
            break

    if steps and all(s["ok"] for s in steps) and not args.skip_mirror:
        steps.append(_run_ps("pr_mirror_sync", "scripts/Sync-PrSasangPromotionMirror_v1.ps1"))
        if not steps[-1]["ok"]:
            pass
        elif not args.skip_pytest:
            for test_path in (
                "tests/test_sasang_interpretive_insight_bundle_v1.py",
                "tests/test_validate_sasang_saju_joint_benchmark_v1.py",
                "tests/test_sasang_rail_p2_v1.py",
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
    elif steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in (
            "tests/test_sasang_interpretive_insight_bundle_v1.py",
            "tests/test_validate_sasang_saju_joint_benchmark_v1.py",
            "tests/test_sasang_rail_p2_v1.py",
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

    gate_path = ROOT / "docs/final/artifacts/sasang_rail_p2_gate_v1_latest.json"
    gate = {}
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "sasang_rail_p2_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p2_gate_ok": gate.get("gate_ok"),
        "sasang_rail_p2_status": gate.get("sasang_rail_p2_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_p2_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["all_ok"], "sasang_rail_p2_status": doc.get("sasang_rail_p2_status")},
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
