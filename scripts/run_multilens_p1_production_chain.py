#!/usr/bin/env python3
"""Orchestrate Multilens P1 production chain (Track A).

Thin wrapper over existing SSOT scripts (CONSTITUTION §11):
  run_p1_efficiency_ab.py (efficiency / intensity / balanced)
  -> report_p1_final_selection.py
  -> optional run_compression_automation_chain.ps1

Use --dry-run or --json-plan to inspect without subprocess side effects.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

OUT_EFFICIENCY = ROOT / "docs/final/artifacts/MULTILENS_P1_AB_EFFICIENCY_V1.json"
OUT_INTENSITY = ROOT / "docs/final/artifacts/MULTILENS_P1_AB_INTENSITY_V1.json"
OUT_BALANCED = ROOT / "docs/final/artifacts/MULTILENS_P1_AB_BALANCED_V1.json"
OUT_FINAL = ROOT / "docs/final/artifacts/MULTILENS_P1_AB_FINAL_SELECTION_V1.json"

PY = sys.executable


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def build_plan(*, include_compression_chain: bool) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for step_id, profile, out_path in (
        ("p1_ab_efficiency", "efficiency_first", OUT_EFFICIENCY),
        ("p1_ab_intensity", "intensity_first", OUT_INTENSITY),
        ("p1_ab_balanced", "balanced", OUT_BALANCED),
    ):
        steps.append(
            {
                "id": step_id,
                "kind": "python",
                "argv": [PY, _rel(ROOT / "scripts/run_p1_efficiency_ab.py"), "--profile", profile],
                "outputs": [_rel(out_path)],
            }
        )
    steps.append(
        {
            "id": "p1_final_selection",
            "kind": "python",
            "argv": [PY, _rel(ROOT / "scripts/report_p1_final_selection.py")],
            "outputs": [_rel(OUT_FINAL)],
        }
    )
    if include_compression_chain:
        steps.append(
            {
                "id": "compression_automation_chain",
                "kind": "powershell",
                "argv": [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    _rel(ROOT / "scripts/run_compression_automation_chain.ps1"),
                ],
                "outputs": [
                    "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
                    "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json",
                ],
                "note": "Refreshes Track A KPI artifacts; run only when explicitly requested.",
            }
        )
    return {
        "schema": "multilens_p1_chain_plan_v1",
        "version": 1,
        "generated_at_utc": _utc_now(),
        "track": "production",
        "workspace_root": _rel(ROOT),
        "ssot_pointer": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §11",
        "include_compression_chain": include_compression_chain,
        "steps": steps,
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Multilens P1 production orchestration (thin wrapper).")
    p.add_argument("--workspace-root", default=str(ROOT), help="Repo root (default: parent of scripts/)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned steps only; do not execute subprocesses.",
    )
    p.add_argument(
        "--json-plan",
        action="store_true",
        help="Emit multilens_p1_chain_plan_v1 JSON (stdout or --plan-out); no subprocesses.",
    )
    p.add_argument("--plan-out", default="", help="Write --json-plan document to this path.")
    p.add_argument(
        "--include-compression-chain",
        action="store_true",
        help="Append run_compression_automation_chain.ps1 (KPI refresh; heavier).",
    )
    return p


def _run_step(step: dict[str, Any], cwd: Path) -> int:
    argv = list(step["argv"])
    print(f"[multilens-p1] >> {' '.join(argv)}", flush=True)
    proc = subprocess.run(argv, cwd=str(cwd), check=False)
    if proc.returncode != 0:
        print(f"[multilens-p1] FAIL {step['id']} exit={proc.returncode}", flush=True)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.workspace_root).resolve()
    global ROOT
    ROOT = root

    plan = build_plan(include_compression_chain=bool(args.include_compression_chain))

    if args.json_plan:
        text = json.dumps(plan, ensure_ascii=False, indent=2)
        if args.plan_out:
            out = Path(args.plan_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
            print(f"WROTE: {out}")
        else:
            print(text)
        return 0

    if args.dry_run:
        print(f"schema={plan['schema']} track={plan['track']} steps={len(plan['steps'])}")
        for i, step in enumerate(plan["steps"], start=1):
            print(f"  {i}. [{step['id']}] {' '.join(step['argv'])}")
        return 0

    for step in plan["steps"]:
        code = _run_step(step, root)
        if code != 0:
            return code

    print("[multilens-p1] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
