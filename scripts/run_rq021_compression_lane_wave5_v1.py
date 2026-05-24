#!/usr/bin/env python3
"""B-track RQ-021 wave5: --hypo-cooc-sidecar on dryrun + per-lane report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
COOC_V2 = ROOT / "reports/other_cooc_cartesian_routing_poc_v2_latest.json"
MIXED_OUT = ROOT / "reports/golden_40_expansion_dryrun_rq021_mixed_cooc_v2_latest.json"
PER_LANE_OUT = ROOT / "reports/golden40_expansion_per_lane_report_v1_latest.json"
WAVE5_OUT = ROOT / "reports/rq021_compression_lane_wave5_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or ""))[-1200:]


def main() -> int:
    ap = argparse.ArgumentParser(description="RQ-021 wave5")
    ap.add_argument("--dryrun-targets", default="40,400")
    ap.add_argument("--out", type=Path, default=WAVE5_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    ec, _ = _run([sys.executable, str(ROOT / "scripts/build_golden40_expansion_per_lane_report_v1.py")])
    steps.append({"step": "per_lane_report", "exit_code": ec})
    if ec != 0:
        _write(args.out, steps, ok=False)
        return ec

    cooc_path = COOC_V2 if COOC_V2.is_file() else None
    dry_cmd = [
        sys.executable,
        str(ROOT / "scripts/run_golden40_expansion_dryrun_v1.py"),
        "--pool-mode",
        "mixed_matrix",
        "--target-counts",
        args.dryrun_targets,
        "--out-json",
        str(MIXED_OUT),
    ]
    if cooc_path:
        dry_cmd.extend(["--hypo-cooc-sidecar", str(cooc_path)])
    ec, tail = _run(dry_cmd)
    steps.append({"step": "mixed_dryrun_cooc_sidecar", "exit_code": ec, "tail": tail[-400:]})

    sidecar_ok = False
    if MIXED_OUT.is_file():
        doc = json.loads(MIXED_OUT.read_text(encoding="utf-8"))
        sidecar_ok = bool((doc.get("hypo_cooc_sidecar") or {}).get("snapshot"))
        kpi_before = (doc.get("tiers") or [{}])[0].get("aggregate_metrics")
        steps.append(
            {
                "step": "sidecar_verify",
                "hypo_cooc_attached": sidecar_ok,
                "kpi_unchanged_note": "sidecar is metadata-only",
                "tier40_jaccard": kpi_before.get("avg_reconstruction_fidelity_jaccard") if kpi_before else None,
            }
        )

    report = json.loads(PER_LANE_OUT.read_text(encoding="utf-8")) if PER_LANE_OUT.is_file() else {}
    verdict = {
        "hypo_cooc_sidecar_wired": sidecar_ok,
        "cooc_v2_proceed": bool((report.get("cooc_routing_v2") or {}).get("proceed_to_bench_hook")),
        "headline_jaccard_golden_core": (report.get("headline_kpi") or {}).get("jaccard"),
        "p4_gate_candidate": False,
        "promotion": "HOLD — human sign-off; FAIL-COMP-004; MS excluded",
    }
    steps.append({"step": "verdict", "verdict": verdict})

    _write(args.out, steps, ok=True, report=report, verdict=verdict)
    print(f"OK: {args.out} cooc_sidecar={sidecar_ok}")
    return 0


def _write(
    out: Path,
    steps: list[dict[str, Any]],
    *,
    ok: bool,
    report: dict[str, Any] | None = None,
    verdict: dict[str, Any] | None = None,
) -> None:
    doc = {
        "schema": "rq021_compression_lane_wave5_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "wave_ok": ok,
        "steps": steps,
        "per_lane_report": report,
        "verdict": verdict,
        "artifacts": {
            "mixed_dryrun": str(MIXED_OUT),
            "per_lane_report": str(PER_LANE_OUT),
            "cooc_v2": str(COOC_V2),
        },
    }
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
