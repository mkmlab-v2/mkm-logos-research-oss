#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_codebook_4d_quaternion_experiment_v1.json"
DEFAULT_AB = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_general_compression_ab_v1.json"
DEFAULT_Q = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_quaternion_generalization_v6.json"
DEFAULT_AB_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE_KPI = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "command": " ".join(cmd),
        "exit_code": int(cp.returncode),
        "stdout": (cp.stdout or "").strip(),
        "stderr": (cp.stderr or "").strip(),
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_run(summary: dict[str, Any], label: str) -> dict[str, Any]:
    for item in summary.get("runs", []):
        if isinstance(item, dict) and item.get("label") == label:
            return item
    return {}


def _f(obj: dict[str, Any], key: str) -> float:
    return float(obj.get(key, 0.0) or 0.0)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run B-track codebook/4D/quaternion experiment bundle.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--ab-out", type=Path, default=DEFAULT_AB)
    ap.add_argument("--ab-input", type=Path, default=DEFAULT_AB_INPUT)
    ap.add_argument("--quat-out", type=Path, default=DEFAULT_Q)
    ap.add_argument("--strategy", choices=("A", "B", "C"), default="C")
    ap.add_argument("--intensity", choices=("high", "ultra", "extreme"), default="extreme")
    ap.add_argument("--general-max-saving-rate", type=float, default=0.52)
    ap.add_argument("--sensitive-max-saving-rate", type=float, default=0.42)
    ap.add_argument("--hangul-max-saving-rate", type=float, default=0.40)
    ap.add_argument("--quat-seeds", default="7,13,29")
    ap.add_argument("--quat-samples-per-cell", type=int, default=60)
    args = ap.parse_args()

    commands: list[dict[str, Any]] = []

    commands.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_general_compression_ab.py"),
                "--label",
                "baseline",
                "--input",
                str(args.ab_input),
                "--out",
                str(args.ab_out),
            ]
        )
    )
    commands.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_general_compression_ab.py"),
                "--label",
                "treatment",
                "--append",
                "--input",
                str(args.ab_input),
                "--out",
                str(args.ab_out),
                "--strategy",
                args.strategy,
                "--intensity",
                args.intensity,
                "--general-max-saving-rate",
                str(args.general_max_saving_rate),
                "--sensitive-max-saving-rate",
                str(args.sensitive_max_saving_rate),
                "--hangul-max-saving-rate",
                str(args.hangul_max_saving_rate),
            ]
        )
    )
    commands.append(
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_trackb_quaternion_generalization_bench_v6.py"),
                "--out",
                str(args.quat_out),
                "--harness-mode",
                "exact_restore_guarded",
                "--eval-metric",
                "exact_sequence",
                "--single-profile",
                "--include-target-in-candidates",
                "--two-stage-ranker",
                "--stage2-swap-guard",
                "--stage2-swap-injection",
                "--stage2-length-prior",
                "--beam-mode",
                "--chunkwise-mode",
                "--lengths",
                "3,5",
                "--oov-ratios",
                "0.0,0.1",
                "--seeds",
                args.quat_seeds,
                "--samples-per-cell",
                str(args.quat_samples_per_cell),
            ]
        )
    )

    failures = [c for c in commands if c["exit_code"] != 0]
    if failures:
        out = {
            "schema": "btrack_codebook_4d_quaternion_experiment_v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "commands": commands,
            "error_count": len(failures),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(args.out.resolve()), "error_count": len(failures)}, ensure_ascii=False))
        return 1

    ab = _load_json(args.ab_out)
    qdoc = _load_json(args.quat_out)
    active = _load_json(ACTIVE_KPI)
    baseline = _find_run(ab, "baseline")
    treatment = _find_run(ab, "treatment")

    baseline_saving = _f(baseline, "global_token_saving_rate")
    treatment_saving = _f(treatment, "global_token_saving_rate")
    baseline_jaccard = _f(baseline, "avg_reconstruction_fidelity_jaccard")
    treatment_jaccard = _f(treatment, "avg_reconstruction_fidelity_jaccard")
    baseline_sensitive = _f(baseline, "avg_sensitive_integrity")
    treatment_sensitive = _f(treatment, "avg_sensitive_integrity")

    active_metrics = (active.get("compression_metrics") or {}) if isinstance(active, dict) else {}
    active_saving = float(active_metrics.get("global_token_saving_rate", 0.0) or 0.0)
    active_jaccard = float(active_metrics.get("avg_reconstruction_fidelity_jaccard", 0.0) or 0.0)
    active_sensitive = float(active_metrics.get("avg_sensitive_integrity", 0.0) or 0.0)

    quat_best = ((qdoc.get("best") or {}).get("min_short_bucket_rate")) or 0.0
    quat_pass = bool(qdoc.get("target_passed", False))

    promotion_candidate = (
        treatment_saving > baseline_saving
        and treatment_jaccard >= 0.60
        and treatment_sensitive >= 0.99
        and quat_best >= 0.90
    )

    result = {
        "schema": "btrack_codebook_4d_quaternion_experiment_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "track_guardrail": "research_only_no_track_a_trigger_change",
        "inputs": {
            "ab_summary": str(args.ab_out.resolve()),
            "quaternion_bench": str(args.quat_out.resolve()),
            "active_kpi": str(ACTIVE_KPI.resolve()),
        },
        "commands": commands,
        "metrics": {
            "baseline": {
                "saving_rate": baseline_saving,
                "reconstruction_jaccard": baseline_jaccard,
                "sensitive_integrity": baseline_sensitive,
            },
            "treatment": {
                "saving_rate": treatment_saving,
                "reconstruction_jaccard": treatment_jaccard,
                "sensitive_integrity": treatment_sensitive,
            },
            "delta_vs_baseline": {
                "saving_rate": treatment_saving - baseline_saving,
                "reconstruction_jaccard": treatment_jaccard - baseline_jaccard,
                "sensitive_integrity": treatment_sensitive - baseline_sensitive,
            },
            "delta_vs_active_kpi": {
                "saving_rate": treatment_saving - active_saving,
                "reconstruction_jaccard": treatment_jaccard - active_jaccard,
                "sensitive_integrity": treatment_sensitive - active_sensitive,
            },
            "quaternion_mapping": {
                "best_min_short_bucket_rate": float(quat_best),
                "target_passed": quat_pass,
            },
        },
        "recommendation": {
            "status": "promotion_candidate" if promotion_candidate else "research_only",
            "reason": (
                "Treatment improved saving with acceptable fidelity/integrity and strong quaternion short-bucket floor."
                if promotion_candidate
                else "Keep as research-only: one or more promotion thresholds not met versus current baselines."
            ),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out.resolve()),
                "recommendation": result["recommendation"]["status"],
                "saving_rate": treatment_saving,
                "jaccard": treatment_jaccard,
                "sensitive_integrity": treatment_sensitive,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
