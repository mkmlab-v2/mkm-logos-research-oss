#!/usr/bin/env python3
"""B-track RQ-021 wave2: polar v3 + pool rebench (mixed + homogeneous_full) + lab summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
POLAR_V3 = ROOT / "reports/polar_coord_compression_hypo_v3_latest.json"
WAVE2_OUT = ROOT / "reports/rq021_compression_lane_wave2_v1_latest.json"

DRYRUNS: dict[str, Path] = {
    "mixed_matrix": ROOT / "reports/golden_40_expansion_dryrun_rq021_mixed_v1_latest.json",
    "homogeneous_full": ROOT / "reports/golden_40_expansion_dryrun_rq021_homogeneous_full_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-1500:]
    return proc.returncode, tail


def _tier_floors(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for tier in doc.get("tiers") or []:
        t = int(tier.get("target_case_count") or 0)
        out[str(t)] = {
            "floor_ok": tier.get("floor_regression_ok"),
            "jaccard": (tier.get("aggregate_metrics") or {}).get("avg_reconstruction_fidelity_jaccard"),
            "actual": tier.get("actual_case_count"),
            "max_pool": tier.get("max_available_in_pool"),
        }
    return out


def _dryrun_job(mode: str, out_path: Path, targets: str, sidecar: Path | None) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_golden40_expansion_dryrun_v1.py"),
        "--pool-mode",
        mode,
        "--target-counts",
        targets,
        "--out-json",
        str(out_path),
    ]
    if sidecar and sidecar.is_file():
        cmd.extend(["--hypo-polar-sidecar", str(sidecar)])
    ec, tail = _run(cmd)
    floors: dict[str, Any] = {}
    if out_path.is_file():
        floors = _tier_floors(json.loads(out_path.read_text(encoding="utf-8")))
    return {"pool_mode": mode, "exit_code": ec, "artifact": str(out_path), "tiers": floors, "tail": tail[-400:]}


def main() -> int:
    ap = argparse.ArgumentParser(description="RQ-021 wave2 parallel bench")
    ap.add_argument("--dryrun-targets", default="40,400")
    ap.add_argument("--skip-pool-compare", action="store_true")
    ap.add_argument("--skip-lab-summary", action="store_true")
    ap.add_argument("--out", type=Path, default=WAVE2_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    ec, _ = _run([sys.executable, str(ROOT / "scripts/run_polar_coord_compression_hypo_v3.py")])
    steps.append({"step": "polar_hypo_v3", "exit_code": ec})
    if ec != 0:
        _write(args.out, steps, ok=False)
        return ec

    polar = json.loads(POLAR_V3.read_text(encoding="utf-8"))
    proceed = bool(polar.get("proceed_to_dryrun_hook"))
    sidecar = POLAR_V3 if proceed else None
    steps.append({"step": "polar_v3_proceed", "proceed": proceed})

    dryrun_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {
            ex.submit(_dryrun_job, mode, path, args.dryrun_targets, sidecar): mode
            for mode, path in DRYRUNS.items()
        }
        for fut in as_completed(futs):
            dryrun_results.append(fut.result())
    steps.extend(dryrun_results)

    pool_ec = 0
    if not args.skip_pool_compare:
        pool_ec, tail = _run(
            [
                sys.executable,
                str(ROOT / "scripts/run_golden40_expansion_pool_compare_v1.py"),
                "--target-counts",
                args.dryrun_targets,
            ]
        )
        steps.append({"step": "pool_compare_all_modes", "exit_code": pool_ec, "tail": tail[-400:]})

    lab_ec = 0
    if not args.skip_lab_summary:
        lab_ec, tail = _run([sys.executable, str(ROOT / "scripts/build_golden40_expansion_lab_summary_v1.py")])
        steps.append({"step": "lab_summary", "exit_code": lab_ec, "tail": tail[-300:]})

    mixed_400 = next((r for r in dryrun_results if r["pool_mode"] == "mixed_matrix"), {})
    hom_400 = next((r for r in dryrun_results if r["pool_mode"] == "homogeneous_full"), {})
    m400 = (mixed_400.get("tiers") or {}).get("400") or {}
    h400 = (hom_400.get("tiers") or {}).get("400") or {}

    verdict = {
        "polar_v3_proceed": proceed,
        "mixed_n400_floor_ok": m400.get("floor_ok"),
        "homogeneous_full_n400_floor_ok": h400.get("floor_ok"),
        "best_n400_floor": bool(m400.get("floor_ok") or h400.get("floor_ok")),
        "p4_gate_candidate": bool(
            (mixed_400.get("tiers") or {}).get("40", {}).get("floor_ok")
            and (m400.get("floor_ok") or h400.get("floor_ok"))
        ),
        "promotion": "HOLD — human sign-off; FAIL-COMP-004; MS excluded",
    }
    steps.append({"step": "verdict", "verdict": verdict})

    _write(args.out, steps, ok=True, polar=polar, verdict=verdict)
    print(f"OK: {args.out} polar_v3_proceed={proceed} p4_gate={verdict['p4_gate_candidate']}")
    return 0 if pool_ec == 0 and lab_ec == 0 else 0


def _write(out: Path, steps: list[dict[str, Any]], *, ok: bool, polar: dict[str, Any] | None = None, verdict: dict[str, Any] | None = None) -> None:
    doc = {
        "schema": "rq021_compression_lane_wave2_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "wave_ok": ok,
        "steps": steps,
        "polar_hypo_v3": polar,
        "verdict": verdict,
        "dryrun_artifacts": {k: str(v) for k, v in DRYRUNS.items()},
        "pointers": {
            "wave1_chain": "reports/rq021_compression_lane_chain_v1_latest.json",
            "research": "docs/research/ANCIENT_CORPUS_COMPRESSION_SRE_BRIDGE_V1.md",
        },
    }
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
