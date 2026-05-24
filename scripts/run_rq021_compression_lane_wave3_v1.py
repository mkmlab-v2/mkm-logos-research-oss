#!/usr/bin/env python3
"""B-track RQ-021 wave3: cooc cartesian routing PoC + golden_core_only dryrun + verdict."""

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
COOC_POC = ROOT / "reports/other_cooc_cartesian_routing_poc_v1_latest.json"
GOLDEN_CORE_OUT = ROOT / "reports/golden_40_expansion_dryrun_rq021_golden_core_v1_latest.json"
WAVE3_OUT = ROOT / "reports/rq021_compression_lane_wave3_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or ""))[-1500:]


def _tier_map(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for tier in doc.get("tiers") or []:
        t = str(int(tier.get("target_case_count") or 0))
        gc = tier.get("golden_core_only_metrics") or tier.get("golden_core_verdict") or {}
        out[t] = {
            "floor_ok": tier.get("floor_regression_ok"),
            "golden_core_floor_ok": (tier.get("golden_core_verdict") or {}).get("floor_regression_ok"),
            "jaccard": (tier.get("aggregate_metrics") or {}).get("avg_reconstruction_fidelity_jaccard"),
            "golden_core_jaccard": gc.get("avg_reconstruction_fidelity_jaccard")
            if isinstance(gc, dict) and "avg_reconstruction_fidelity_jaccard" in gc
            else (tier.get("golden_core_only_metrics") or {}).get("avg_reconstruction_fidelity_jaccard"),
            "actual": tier.get("actual_case_count"),
        }
    return out


def _golden_core_job(targets: str) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_golden40_expansion_dryrun_v1.py"),
        "--pool-mode",
        "golden_core_only",
        "--target-counts",
        targets,
        "--out-json",
        str(GOLDEN_CORE_OUT),
    ]
    ec, tail = _run(cmd)
    tiers: dict[str, Any] = {}
    if GOLDEN_CORE_OUT.is_file():
        tiers = _tier_map(json.loads(GOLDEN_CORE_OUT.read_text(encoding="utf-8")))
    return {"step": "golden_core_only_dryrun", "exit_code": ec, "tiers": tiers, "tail": tail[-400:]}


def main() -> int:
    ap = argparse.ArgumentParser(description="RQ-021 wave3")
    ap.add_argument("--dryrun-targets", default="40,400")
    ap.add_argument("--out", type=Path, default=WAVE3_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    ec, _ = _run([sys.executable, str(ROOT / "scripts/run_other_cooc_cartesian_routing_poc_v1.py")])
    steps.append({"step": "cooc_cartesian_routing_poc", "exit_code": ec})
    if ec != 0:
        _write(args.out, steps, ok=False)
        return ec

    cooc = json.loads(COOC_POC.read_text(encoding="utf-8")) if COOC_POC.is_file() else {}
    proceed_cooc = bool(cooc.get("proceed_to_bench_hook"))
    steps.append({"step": "cooc_proceed", "proceed": proceed_cooc})

    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(_golden_core_job, args.dryrun_targets)
        steps.append(fut.result())

    gc_tiers = steps[-1].get("tiers") or {}
    t40 = gc_tiers.get("40") or {}
    t400 = gc_tiers.get("400") or {}

    verdict = {
        "cooc_routing_proceed": proceed_cooc,
        "cooc_f1": (cooc.get("recommended_metrics") or {}).get("f1"),
        "cooc_recall": (cooc.get("recommended_metrics") or {}).get("recall"),
        "golden_core_n40_floor_ok": t40.get("golden_core_floor_ok") or t40.get("floor_ok"),
        "golden_core_n400_jaccard": t400.get("golden_core_jaccard"),
        "golden_core_n400_floor_ok": t400.get("golden_core_floor_ok"),
        "expansion_dilution_hypothesis": (
            "N400 blended floor fails while golden_core ~0.873 — isolate expansion lanes [HYPO]"
        ),
        "p4_gate_candidate": False,
        "promotion": "HOLD — human sign-off; FAIL-COMP-004; MS excluded",
    }
    steps.append({"step": "verdict", "verdict": verdict})

    _write(args.out, steps, ok=True, cooc=cooc, verdict=verdict)
    print(f"OK: {args.out} cooc_proceed={proceed_cooc} gc400_jaccard={t400.get('golden_core_jaccard')}")
    return 0


def _write(
    out: Path,
    steps: list[dict[str, Any]],
    *,
    ok: bool,
    cooc: dict[str, Any] | None = None,
    verdict: dict[str, Any] | None = None,
) -> None:
    doc = {
        "schema": "rq021_compression_lane_wave3_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "wave_ok": ok,
        "steps": steps,
        "cooc_routing_poc": cooc,
        "verdict": verdict,
        "artifacts": {
            "cooc_poc": str(COOC_POC),
            "golden_core_dryrun": str(GOLDEN_CORE_OUT),
            "wave2": "reports/rq021_compression_lane_wave2_v1_latest.json",
        },
    }
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
