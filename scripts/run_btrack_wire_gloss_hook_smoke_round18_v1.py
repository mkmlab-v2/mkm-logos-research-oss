#!/usr/bin/env python3
"""B-track Round 18: wire gloss hook smoke (surface reconstruct + cap dryrun sidecar)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LANE = ROOT / "reports/golden_40_logos_verse_compression_lane_stride120_v1.json"
POLICY = ROOT / "reports/logos_verse_per_lane_ssot_cap_policy_v1_latest.json"
OUT = ROOT / "reports/btrack_wire_gloss_hook_smoke_round18_v1_latest.json"
SURFACE_OUT = ROOT / "reports/logos_verse_surface_reconstruct_wire_gloss_v1_latest.json"
DRYRUN_OUT = ROOT / "reports/golden_40_expansion_dryrun_logos_cap015_wire_gloss_sidecar_v1_latest.json"
R17 = ROOT / "reports/btrack_wire_gloss_remediation_round17_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _surface_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"missing": True}
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema": doc.get("schema"),
        "case_count": doc.get("case_count"),
        "mean_jaccard_base": doc.get("mean_jaccard_base"),
        "mean_jaccard_surface": doc.get("mean_jaccard_surface") or doc.get("mean_jaccard_surface_wire_gloss"),
        "surface_delta_pp": doc.get("surface_delta_pp") or doc.get("wire_gloss_delta_pp_vs_lexicon"),
        "proceed_hook": doc.get("proceed_hook"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Wire gloss hook smoke round 18")
    ap.add_argument("--sample-count", type=int, default=48)
    ap.add_argument("--skip-dryrun", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    cap = str(args.sample_count)

    ec_b, _ = _run(
        [
            sys.executable,
            "scripts/logos_verse_surface_reconstruct_hypo_v1.py",
            "--cases-json",
            str(LANE),
            "--cap",
            cap,
            "--wire-gloss",
            "none",
            "--out-json",
            str(ROOT / "reports/tmp_surface_baseline_r18.json"),
        ]
    )
    steps.append({"step": "surface_baseline", "exit_code": ec_b})

    ec_w, _ = _run(
        [
            sys.executable,
            "scripts/logos_verse_surface_reconstruct_hypo_v1.py",
            "--cases-json",
            str(LANE),
            "--cap",
            cap,
            "--wire-gloss",
            "per_case",
            "--out-json",
            str(SURFACE_OUT),
        ]
    )
    steps.append({"step": "surface_wire_gloss_per_case", "exit_code": ec_w})

    dryrun_j: float | None = None
    if not args.skip_dryrun:
        ec_d, tail_d = _run(
            [
                sys.executable,
                "scripts/run_golden40_expansion_dryrun_v1.py",
                "--pool-mode",
                "homogeneous_logos_verse",
                "--logos-verse-lane",
                str(LANE),
                "--target-counts",
                cap,
                "--apply-per-lane-cap-policy",
                "--per-lane-cap-policy",
                str(POLICY),
                "--hypo-wire-gloss-sidecar",
                str(R17),
                "--out-json",
                str(DRYRUN_OUT),
            ]
        )
        steps.append({"step": "logos_cap_dryrun_wire_gloss_sidecar", "exit_code": ec_d, "tail": tail_d[-1200:]})
        if DRYRUN_OUT.is_file():
            tier = (json.loads(DRYRUN_OUT.read_text(encoding="utf-8")).get("tiers") or [{}])[-1]
            m = tier.get("aggregate_metrics") or {}
            dryrun_j = float(m.get("avg_reconstruction_fidelity_jaccard") or 0) or None

    baseline = _surface_summary(ROOT / "reports/tmp_surface_baseline_r18.json")
    wire = _surface_summary(SURFACE_OUT)

    hook_ok = (
        ec_w == 0
        and wire.get("proceed_hook") is False
        and (wire.get("surface_delta_pp") or 0) == 0
    )
    # proceed_hook false + 0pp is expected — hook wired correctly, no false uplift claim

    doc: dict[str, Any] = {
        "schema": "btrack_wire_gloss_hook_smoke_round18_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "would_change_active": False,
        "lane_id": "wire_gloss_lexicon_aligned_v1",
        "sample_count": args.sample_count,
        "surface_baseline": baseline,
        "surface_wire_gloss_per_case": wire,
        "dryrun_cap015_mean_jaccard": dryrun_j,
        "hook_wired_ok": ec_w == 0 and wire.get("case_count", 0) > 0,
        "decoder_uplift_pp": wire.get("surface_delta_pp"),
        "verdict": (
            "Hook wired; decoder uplift 0pp as expected (cap bind remains dominant lever)."
            if hook_ok or (ec_w == 0 and wire.get("surface_delta_pp") == 0)
            else "Check surface or dryrun step failures."
        ),
        "artifacts": {
            "surface_wire_gloss": str(SURFACE_OUT.relative_to(ROOT)).replace("\\", "/"),
            "dryrun_sidecar": str(DRYRUN_OUT.relative_to(ROOT)).replace("\\", "/") if DRYRUN_OUT.is_file() else None,
            "round17": str(R17.relative_to(ROOT)).replace("\\", "/"),
        },
        "steps": steps,
        "next": "Wire gloss sidecar attached to dryrun metadata only; evaluate_report graph_wire hook remains future work.",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["hook_wired_ok"],
                "out": str(OUT),
                "wire_gloss_delta_pp": wire.get("surface_delta_pp"),
                "dryrun_j": dryrun_j,
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["hook_wired_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
