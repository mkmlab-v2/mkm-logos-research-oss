#!/usr/bin/env python3
"""Synthetic 120d weather GT → triplet registry → Brier/ECE eval (B-track, [HYPO]).

Default: generate 120-row synthetic CSV, run triplet chain with --auto-forecasts-sidecar,
then eval_general_prophecy_brier_score.py (--no-rows, --ece-bins 10).

--stub-only: registry with fixed p=0.5 (baseline mean Brier ≈ 0.25 on balanced binary).
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

DEFAULT_CSV = ROOT / "tests" / "fixtures" / "weather_ground_truth_synthetic_120d_input.csv"
DEFAULT_JSONL = ROOT / "reports" / "weather_ground_truth_synthetic_120d_latest.jsonl"
DEFAULT_REGISTRY_SIDECAR = ROOT / "docs" / "final" / "artifacts" / "weather_prophecy_triplet_synthetic_120d_v1.json"
DEFAULT_REGISTRY_STUB = ROOT / "docs" / "final" / "artifacts" / "weather_prophecy_triplet_synthetic_120d_stub_v1.json"
DEFAULT_BRIER_SIDECAR = ROOT / "docs" / "final" / "artifacts" / "weather_prophecy_brier_eval_synthetic_120d_sidecar_summary_v1.json"
DEFAULT_BRIER_STUB = ROOT / "docs" / "final" / "artifacts" / "weather_prophecy_brier_eval_synthetic_120d_summary_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print("[120d]", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def _write_summary(*, brier_path: Path, summary_path: Path, mode: str, registry_path: Path, jsonl_path: Path) -> None:
    brier_doc = json.loads(brier_path.read_text(encoding="utf-8"))
    summary: dict[str, Any] = {
        "schema": "weather_prophecy_brier_eval_synthetic_120d_summary_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "mode": mode,
        "inputs": {
            "ground_truth_jsonl": str(jsonl_path),
            "registry_json": str(registry_path),
            "brier_eval_json": str(brier_path),
        },
        "metrics": brier_doc.get("metrics") or {},
        "note": "Synthetic 120d bulk eval; not KMA truth; B-track calibration only.",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--registry-json", type=Path, default=None)
    ap.add_argument("--brier-out", type=Path, default=None)
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--start-date", default="2015-06-01")
    ap.add_argument("--stub-only", action="store_true")
    ap.add_argument("--ece-bins", type=int, default=10)
    ap.add_argument("--ece-min-per-tag", type=int, default=5)
    ap.add_argument("--skip-csv-generate", action="store_true")
    ap.add_argument("--threshold-mm", type=float, default=0.1)
    ns = ap.parse_args()

    if ns.registry_json is None:
        ns.registry_json = DEFAULT_REGISTRY_STUB if ns.stub_only else DEFAULT_REGISTRY_SIDECAR
    if ns.brier_out is None:
        ns.brier_out = DEFAULT_BRIER_STUB if ns.stub_only else DEFAULT_BRIER_SIDECAR

    if not ns.skip_csv_generate:
        rc = _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_weather_gt_synthetic_csv_v1.py"),
                "--output",
                str(ns.csv),
                "--days",
                str(ns.days),
                "--start-date",
                ns.start_date,
            ]
        )
        if rc != 0:
            return rc

    chain_args = [
        sys.executable,
        str(ROOT / "scripts" / "run_weather_gt_to_prophecy_triplet_chain_v1.py"),
        "--input-csv",
        str(ns.csv),
        "--gt-jsonl",
        str(ns.jsonl),
        "--registry-out",
        str(ns.registry_json),
    ]
    if ns.stub_only:
        # Build via direct registry step with stub probability (no sidecar).
        rc = _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "csv_to_weather_ground_truth_jsonl_v1.py"),
                "--input",
                str(ns.csv),
                "--output",
                str(ns.jsonl),
            ]
        )
        if rc != 0:
            return rc
        rc = _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_weather_ground_truth_jsonl_v1.py"),
                "--input",
                str(ns.jsonl),
                "--threshold-mm",
                str(ns.threshold_mm),
            ]
        )
        if rc != 0:
            return rc
        rc = _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_weather_triplet_registry_v1.py"),
                "--input",
                str(ns.jsonl),
                "--output",
                str(ns.registry_json),
                "--stub-probability",
                "0.5",
            ]
        )
        if rc != 0:
            return rc
    else:
        chain_args.append("--auto-forecasts-sidecar")
        rc = _run(chain_args)
        if rc != 0:
            return rc

    eval_args = [
        sys.executable,
        str(ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
        "--input",
        str(ns.registry_json),
        "--output",
        str(ns.brier_out),
        "--no-rows",
        "--no-print-output-path",
        "--ece-bins",
        str(ns.ece_bins),
        "--ece-min-per-tag",
        str(ns.ece_min_per_tag),
    ]
    rc = _run(eval_args)
    if rc != 0:
        return rc

    mode = "stub_only" if ns.stub_only else "auto_forecasts_sidecar"
    _write_summary(
        brier_path=ns.brier_out,
        summary_path=ns.brier_out,
        mode=mode,
        registry_path=ns.registry_json,
        jsonl_path=ns.jsonl,
    )
    metrics = json.loads(ns.brier_out.read_text(encoding="utf-8")).get("metrics") or {}
    mean_brier = metrics.get("mean_brier_score")
    print(
        f"DONE mode={mode} mean_brier={mean_brier} n={metrics.get('n_evaluated')} "
        f"registry={ns.registry_json} brier={ns.brier_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
