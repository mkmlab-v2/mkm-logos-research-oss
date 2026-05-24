#!/usr/bin/env python3
"""B-track RQ-021 wave4: prefix-gated cooc v2 + per-lane dryruns + isolation summary."""

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
COOC_V2 = ROOT / "reports/other_cooc_cartesian_routing_poc_v2_latest.json"
WAVE4_OUT = ROOT / "reports/rq021_compression_lane_wave4_v1_latest.json"

LANE_DRYRUNS: dict[str, Path] = {
    "homogeneous_sasang_ko": ROOT / "reports/golden_40_expansion_dryrun_rq021_sasang_v1_latest.json",
    "homogeneous_logos_verse": ROOT / "reports/golden_40_expansion_dryrun_rq021_logos_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or ""))[-1200:]


def _dryrun(pool_mode: str, out_path: Path, targets: str, sidecar: Path | None) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_golden40_expansion_dryrun_v1.py"),
        "--pool-mode",
        pool_mode,
        "--target-counts",
        targets,
        "--out-json",
        str(out_path),
    ]
    if sidecar and sidecar.is_file():
        cmd.extend(["--hypo-cooc-sidecar", str(sidecar)])
    ec, tail = _run(cmd)
    return {"pool_mode": pool_mode, "exit_code": ec, "artifact": str(out_path), "tail": tail[-350:]}


def main() -> int:
    ap = argparse.ArgumentParser(description="RQ-021 wave4")
    ap.add_argument("--dryrun-targets", default="40,400")
    ap.add_argument("--out", type=Path, default=WAVE4_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    ec, _ = _run([sys.executable, str(ROOT / "scripts/run_other_cooc_cartesian_routing_poc_v2.py")])
    steps.append({"step": "cooc_routing_poc_v2", "exit_code": ec})
    if ec != 0:
        _write(args.out, steps, ok=False)
        return ec

    cooc = json.loads(COOC_V2.read_text(encoding="utf-8")) if COOC_V2.is_file() else {}
    proceed = bool(cooc.get("proceed_to_bench_hook"))
    steps.append({"step": "cooc_v2_proceed", "proceed": proceed})

    sidecar = COOC_V2 if proceed else None
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [
            ex.submit(_dryrun, mode, path, args.dryrun_targets, sidecar)
            for mode, path in LANE_DRYRUNS.items()
        ]
        for fut in as_completed(futs):
            steps.append(fut.result())

    ec, tail = _run([sys.executable, str(ROOT / "scripts/build_golden40_expansion_lane_isolation_summary_v1.py")])
    steps.append({"step": "lane_isolation_summary", "exit_code": ec, "tail": tail[-300:]})

    iso_path = ROOT / "reports/golden40_expansion_lane_isolation_summary_v1_latest.json"
    iso = json.loads(iso_path.read_text(encoding="utf-8")) if iso_path.is_file() else {}

    verdict = {
        "cooc_v2_proceed": proceed,
        "within_other_separation_ratio": (cooc.get("within_other_separation") or {}).get("separation_ratio"),
        "isolate_high_count": (cooc.get("tiers") or {}).get("isolate_high", {}).get("count"),
        "expansion_dilution_modes": (iso.get("verdict") or {}).get("expansion_dilution_modes"),
        "p4_gate_candidate": False,
        "promotion": "HOLD — human sign-off; FAIL-COMP-004; MS excluded",
    }
    steps.append({"step": "verdict", "verdict": verdict})

    _write(args.out, steps, ok=True, cooc=cooc, verdict=verdict, iso=iso)
    print(f"OK: {args.out} cooc_v2_proceed={proceed}")
    return 0


def _write(
    out: Path,
    steps: list[dict[str, Any]],
    *,
    ok: bool,
    cooc: dict[str, Any] | None = None,
    verdict: dict[str, Any] | None = None,
    iso: dict[str, Any] | None = None,
) -> None:
    doc = {
        "schema": "rq021_compression_lane_wave4_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "wave_ok": ok,
        "steps": steps,
        "cooc_routing_poc_v2": cooc,
        "lane_isolation_summary": iso,
        "verdict": verdict,
    }
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
