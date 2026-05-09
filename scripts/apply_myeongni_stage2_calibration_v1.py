#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CAL = ART / "myeongni_stage2_calibration_report_latest.json"
DEFAULT_OVERRIDE_OUT = ART / "myeongni_stage2_threshold_override_latest.json"
DEFAULT_BASELINE_OUT = ART / "mkm_myeongni_response_v2_stage2_baseline_latest.json"
DEFAULT_APPLIED_OUT = ART / "mkm_myeongni_response_v2_stage2_latest.json"
DEFAULT_DIFF_OUT = ART / "myeongni_stage2_apply_diff_report_latest.json"
DEFAULT_DIST_OUT = ART / "myeongni_stage2_distribution_stability_report_latest.json"
DEFAULT_REALSET_GATE_OUT = ART / "myeongni_stage2_realset_gate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Apply stage2 calibration thresholds and generate before/after diff report."
    )
    ap.add_argument("--calibration-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--profile", choices=("conservative", "balanced", "attack"), default="balanced")
    ap.add_argument("--track", choices=("A", "B"), default="B")
    ap.add_argument("--actor", default="athena")
    ap.add_argument("--reason", default="stage2_real_data_calibration_apply")
    ap.add_argument("--override-output-json", type=Path, default=DEFAULT_OVERRIDE_OUT)
    ap.add_argument("--baseline-output-json", type=Path, default=DEFAULT_BASELINE_OUT)
    ap.add_argument("--applied-output-json", type=Path, default=DEFAULT_APPLIED_OUT)
    ap.add_argument("--diff-output-json", type=Path, default=DEFAULT_DIFF_OUT)
    ap.add_argument("--distribution-output-json", type=Path, default=DEFAULT_DIST_OUT)
    ap.add_argument("--distribution-target-samples", type=int, default=60)
    ap.add_argument("--distribution-seed", type=int, default=42)
    ap.add_argument("--realset-gate-output-json", type=Path, default=DEFAULT_REALSET_GATE_OUT)
    ap.add_argument("--realset-min-count", type=int, default=50)
    ap.add_argument("--strict-realset-gate", action="store_true")
    args = ap.parse_args()

    cal_path = args.calibration_json if args.calibration_json.is_absolute() else ROOT / args.calibration_json
    cal = _read_json(cal_path)
    best = cal.get("best_thresholds") if isinstance(cal.get("best_thresholds"), dict) else {}
    hold_cut = best.get("hold_confidence_cut")
    reduce_d_cut = best.get("reduce_direction_cut")
    reduce_c_cut = best.get("reduce_confidence_cut")
    if not all(isinstance(v, (int, float)) for v in (hold_cut, reduce_d_cut, reduce_c_cut)):
        raise SystemExit("invalid calibration report: best_thresholds missing numeric cuts")

    override_doc = {
        "schema": "myeongni_stage2_threshold_override_v1",
        "applied_at_utc": _now(),
        "actor": str(args.actor),
        "reason": str(args.reason),
        "source_calibration_json": str(cal_path.resolve()),
        "track": args.track,
        "profile_baseline": args.profile,
        "thresholds": {
            "hold_confidence_cut": float(hold_cut),
            "reduce_direction_cut": float(reduce_d_cut),
            "reduce_confidence_cut": float(reduce_c_cut),
        },
    }
    override_out = args.override_output_json if args.override_output_json.is_absolute() else ROOT / args.override_output_json
    override_out.parent.mkdir(parents=True, exist_ok=True)
    override_out.write_text(json.dumps(override_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    baseline_out = args.baseline_output_json if args.baseline_output_json.is_absolute() else ROOT / args.baseline_output_json
    applied_out = args.applied_output_json if args.applied_output_json.is_absolute() else ROOT / args.applied_output_json
    diff_out = args.diff_output_json if args.diff_output_json.is_absolute() else ROOT / args.diff_output_json
    dist_out = (
        args.distribution_output_json
        if args.distribution_output_json.is_absolute()
        else ROOT / args.distribution_output_json
    )
    realset_gate_out = (
        args.realset_gate_output_json
        if args.realset_gate_output_json.is_absolute()
        else ROOT / args.realset_gate_output_json
    )

    # 1) Baseline run with existing profile defaults
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_mkm_myeongni_response_v2.py"),
            "--profile",
            args.profile,
            "--track",
            args.track,
            "--output-json",
            str(baseline_out),
        ]
    )

    # 2) Applied run with calibrated cuts
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_mkm_myeongni_response_v2.py"),
            "--profile",
            args.profile,
            "--track",
            args.track,
            "--hold-confidence-cut",
            str(hold_cut),
            "--reduce-direction-cut",
            str(reduce_d_cut),
            "--reduce-confidence-cut",
            str(reduce_c_cut),
            "--output-json",
            str(applied_out),
        ]
    )

    # 3) Build before/after diff report
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_myeongni_stage2_apply_diff_report_v1.py"),
            "--calibration-json",
            str(cal_path),
            "--baseline-json",
            str(baseline_out),
            "--applied-json",
            str(applied_out),
            "--output-json",
            str(diff_out),
        ]
    )

    # 4) Build distribution stability report (real + deterministic synthetic expansion)
    _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_myeongni_stage2_distribution_report_v1.py"),
            "--calibration-json",
            str(cal_path),
            "--baseline-json",
            str(baseline_out),
            "--override-json",
            str(override_out),
            "--target-sample-count",
            str(int(args.distribution_target_samples)),
            "--seed",
            str(int(args.distribution_seed)),
            "--output-json",
            str(dist_out),
        ]
    )

    # 5) Real-set gate (50+ target by default)
    realset_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_myeongni_stage2_realset_gate_v1.py"),
        "--search-dir",
        str(ART),
        "--min-real-count",
        str(int(args.realset_min_count)),
        "--output-json",
        str(realset_gate_out),
    ]
    if args.strict_realset_gate:
        realset_cmd.append("--strict")
    _run(realset_cmd)

    print(
        json.dumps(
            {
                "ok": True,
                "override": str(override_out),
                "baseline": str(baseline_out),
                "applied": str(applied_out),
                "diff": str(diff_out),
                "distribution": str(dist_out),
                "realset_gate": str(realset_gate_out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
