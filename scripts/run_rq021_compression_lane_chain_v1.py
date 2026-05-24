#!/usr/bin/env python3
"""B-track RQ-021: run polar hypo v2 -> golden40 dryrun (40+400) -> chain summary. MS/ACTIVE untouched."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
POLAR_V2 = ROOT / "reports/polar_coord_compression_hypo_v2_latest.json"
DRYRUN_OUT = ROOT / "reports/golden_40_expansion_dryrun_rq021_polar_v1_latest.json"
CHAIN_OUT = ROOT / "reports/rq021_compression_lane_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path = ROOT) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    tail = (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:]
    return proc.returncode, tail


def main() -> int:
    ap = argparse.ArgumentParser(description="RQ-021 compression lane chain (B-track)")
    ap.add_argument("--skip-dryrun", action="store_true", help="Polar v2 only")
    ap.add_argument("--dryrun-targets", default="40,400")
    ap.add_argument("--out", type=Path, default=CHAIN_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    ec, _ = _run([sys.executable, str(ROOT / "scripts/run_polar_coord_compression_hypo_v2.py")])
    steps.append({"step": "polar_hypo_v2", "exit_code": ec})
    if ec != 0:
        _write_chain(args.out, steps, ok=False)
        return ec

    polar = json.loads(POLAR_V2.read_text(encoding="utf-8")) if POLAR_V2.is_file() else {}
    proceed = bool(polar.get("proceed_to_dryrun_hook"))

    if not args.skip_dryrun:
        dry_cmd = [
            sys.executable,
            str(ROOT / "scripts/run_golden40_expansion_dryrun_v1.py"),
            "--target-counts",
            args.dryrun_targets,
            "--out-json",
            str(DRYRUN_OUT),
        ]
        if proceed and POLAR_V2.is_file():
            dry_cmd.extend(["--hypo-polar-sidecar", str(POLAR_V2)])
        ec, tail = _run(dry_cmd)
        steps.append({"step": "golden40_dryrun", "exit_code": ec, "tail": tail[-500:]})
        # Floor regression FAIL still writes dryrun JSON — continue to verdict (B-track HOLD).

    dry_doc: dict[str, Any] = {}
    if DRYRUN_OUT.is_file():
        dry_doc = json.loads(DRYRUN_OUT.read_text(encoding="utf-8"))

    n400_floor = None
    n40_floor = None
    for tier in dry_doc.get("tiers") or []:
        t = int(tier.get("target_case_count") or 0)
        if t == 400:
            n400_floor = tier.get("floor_regression_ok")
        if t == 40:
            n40_floor = tier.get("floor_regression_ok")

    verdict = {
        "polar_v2_proceed": proceed,
        "n40_floor_ok": n40_floor,
        "n400_floor_ok": n400_floor,
        "p4_gate_candidate": bool(n40_floor and n400_floor),
        "promotion": "HOLD — human sign-off; FAIL-COMP-004; MS excluded",
    }
    steps.append({"step": "verdict", "verdict": verdict})

    _write_chain(args.out, steps, ok=True, polar=polar, verdict=verdict, dryrun_path=str(DRYRUN_OUT))
    print(f"OK: {args.out} p4_gate_candidate={verdict['p4_gate_candidate']}")
    return 0


def _write_chain(
    out: Path,
    steps: list[dict[str, Any]],
    *,
    ok: bool,
    polar: dict[str, Any] | None = None,
    verdict: dict[str, Any] | None = None,
    dryrun_path: str | None = None,
) -> None:
    doc = {
        "schema": "rq021_compression_lane_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "chain_ok": ok,
        "steps": steps,
        "polar_hypo_v2": polar,
        "verdict": verdict,
        "dryrun_artifact": dryrun_path,
        "pointers": {
            "research": "docs/research/ANCIENT_CORPUS_COMPRESSION_SRE_BRIDGE_V1.md",
            "bridge": "docs/final/artifacts/ancient_corpus_compression_sre_bridge_pointer_v1_latest.json",
        },
    }
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
