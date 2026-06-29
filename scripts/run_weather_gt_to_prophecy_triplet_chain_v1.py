#!/usr/bin/env python3
"""One-click weather ground-truth → general_prophecy triplet chain (B-track, [HYPO]).

Orchestrates documented sub-steps from CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md.
Exits 2 when required pipeline scripts are absent (Fact-Lock drift guard).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRIFT_OUT = ROOT / "docs/final/artifacts/weather_gt_triplet_chain_drift_v1_latest.json"

REQUIRED_SCRIPTS = (
    "csv_to_weather_ground_truth_jsonl_v1.py",
    "validate_weather_ground_truth_jsonl_v1.py",
    "build_weather_triplet_registry_v1.py",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _missing_scripts() -> list[str]:
    scripts_dir = ROOT / "scripts"
    missing: list[str] = []
    for name in REQUIRED_SCRIPTS:
        if not (scripts_dir / name).is_file():
            missing.append(name)
    return missing


def _write_drift_report(*, missing: list[str], out: Path) -> None:
    doc: dict[str, Any] = {
        "schema": "weather_gt_triplet_chain_drift_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "entrypoint": "scripts/run_weather_gt_to_prophecy_triplet_chain_v1.py",
        "status": "pipeline_subscripts_missing",
        "missing_scripts": missing,
        "note": "Restore documented weather pipeline scripts before running full chain.",
        "constitution_pointer": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md (기상 관측 라벨)",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_py(script: str, args: list[str]) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *args]
    print("[chain]", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-csv", type=Path, default=None, help="Weather CSV input (step 1).")
    ap.add_argument("--gt-jsonl", type=Path, default=None, help="Existing ground-truth JSONL (skip CSV step).")
    ap.add_argument("--registry-out", type=Path, default=ROOT / "docs/final/artifacts/weather_prophecy_triplet_latest.json")
    ap.add_argument("--skip-validate-jsonl", action="store_true")
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--forecasts-jsonl", type=Path, default=None)
    ap.add_argument("--auto-forecasts-sidecar", action="store_true")
    ap.add_argument("--drift-out", type=Path, default=DEFAULT_DRIFT_OUT)
    ap.add_argument(
        "--status-only",
        action="store_true",
        help="Only report missing sub-scripts; exit 0 if entrypoint present.",
    )
    ns = ap.parse_args()

    missing = _missing_scripts()
    if missing:
        _write_drift_report(missing=missing, out=ns.drift_out)
        print(f"DRIFT: missing {len(missing)} sub-script(s) → {ns.drift_out}", file=sys.stderr)
        for m in missing:
            print(f"  - scripts/{m}", file=sys.stderr)
        if ns.status_only:
            return 0
        return 2

    if ns.status_only:
        print("OK: weather triplet chain entrypoint + required sub-scripts present")
        return 0

    gt_jsonl = ns.gt_jsonl
    if ns.input_csv is not None:
        if gt_jsonl is None:
            gt_jsonl = ROOT / "reports" / "weather_ground_truth_latest.jsonl"
        step_args = ["--input", str(ns.input_csv), "--output", str(gt_jsonl)]
        if ns.max_rows is not None:
            step_args.extend(["--max-rows", str(ns.max_rows)])
        rc = _run_py("csv_to_weather_ground_truth_jsonl_v1.py", step_args)
        if rc != 0:
            return rc
    elif gt_jsonl is None:
        print("provide --input-csv or --gt-jsonl", file=sys.stderr)
        return 2

    if not ns.skip_validate_jsonl:
        rc = _run_py("validate_weather_ground_truth_jsonl_v1.py", ["--input", str(gt_jsonl)])
        if rc != 0:
            return rc

    reg_args = ["--input", str(gt_jsonl), "--output", str(ns.registry_out)]
    if ns.forecasts_jsonl is not None:
        reg_args.extend(["--forecasts-jsonl", str(ns.forecasts_jsonl)])
    if ns.auto_forecasts_sidecar:
        reg_args.append("--auto-forecasts-sidecar")
    rc = _run_py("build_weather_triplet_registry_v1.py", reg_args)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
