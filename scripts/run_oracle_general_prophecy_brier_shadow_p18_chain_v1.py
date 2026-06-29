#!/usr/bin/env python3
"""P18 general_prophecy Brier/ECE shadow eval — oracle lane (B-track, HYPO).

Wraps existing predictability harness + 120d weather synthetic calibration.
Does not ingest Logos GraphRAG or mutate verse/router SSOT.

Reproducible:
  py scripts/run_oracle_general_prophecy_brier_shadow_p18_chain_v1.py
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
HARNESS_OUT = ROOT / "reports/btrack_predictability_harness_v1_latest.json"
BRIER_PROD = ROOT / "docs/final/artifacts/general_prophecy_brier_eval_latest.json"
WEATHER_SIDECAR = (
    ROOT / "docs/final/artifacts/weather_prophecy_brier_eval_synthetic_120d_sidecar_summary_v1.json"
)
WEATHER_STUB = ROOT / "docs/final/artifacts/weather_prophecy_brier_eval_synthetic_120d_summary_v1.json"
CHAIN_OUT = ROOT / "reports/oracle_general_prophecy_brier_shadow_p18_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _mean_brier(path: Path) -> float | None:
    if not path.is_file():
        return None
    doc = _load(path)
    metrics = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else doc
    val = metrics.get("mean_brier_score")
    return float(val) if val is not None else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-harness-append", action="store_true", help="Pass --skip-append to harness")
    parser.add_argument("--ece-bins", type=int, default=10)
    parser.add_argument("--ece-min-per-tag", type=int, default=5)
    parser.add_argument("--out-json", type=Path, default=CHAIN_OUT)
    args = parser.parse_args()

    steps: list[dict[str, Any]] = []
    ece = ["--ece-bins", str(args.ece_bins), "--ece-min-per-tag", str(args.ece_min_per_tag)]

    harness_cmd = [sys.executable, "scripts/run_btrack_predictability_harness_v1.py", *ece]
    if args.skip_harness_append:
        harness_cmd.append("--skip-append")
    proc = subprocess.run(harness_cmd, cwd=ROOT, check=False)
    steps.append({"step": "predictability_harness", "exit_code": proc.returncode})
    if proc.returncode != 0:
        print(f"FAIL: predictability harness exit {proc.returncode}", file=sys.stderr)
        return proc.returncode
    print("OK: run_btrack_predictability_harness_v1.py")

    if not HARNESS_OUT.is_file():
        print(f"FAIL: missing {HARNESS_OUT}", file=sys.stderr)
        return 1
    harness = _load(HARNESS_OUT)
    if not harness.get("harness_pass"):
        print("FAIL: harness_pass false", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [sys.executable, "scripts/run_weather_synthetic_120d_chain_and_brier_v1.py", *ece],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "weather_120d_sidecar", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode
    print("OK: weather 120d sidecar chain")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_weather_synthetic_120d_chain_and_brier_v1.py",
            "--stub-only",
            *ece,
        ],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "weather_120d_stub", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode
    print("OK: weather 120d stub baseline")

    prod_brier = _mean_brier(BRIER_PROD)
    sidecar_brier = _mean_brier(WEATHER_SIDECAR)
    stub_brier = _mean_brier(WEATHER_STUB)

    if sidecar_brier is None or stub_brier is None:
        print("FAIL: missing weather brier summaries", file=sys.stderr)
        return 1
    if sidecar_brier >= 0.05:
        print(f"FAIL: sidecar mean_brier {sidecar_brier} >= 0.05", file=sys.stderr)
        return 1
    if abs(stub_brier - 0.25) >= 1e-9:
        print(f"FAIL: stub mean_brier {stub_brier} != 0.25", file=sys.stderr)
        return 1

    report = {
        "schema": "oracle_general_prophecy_brier_shadow_p18_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_wall": "no_logos_verse_ssot_mutation",
        "chain_pass": True,
        "steps": steps,
        "metrics": {
            "production_registry": {
                "harness_pass": True,
                "mean_brier_score": prod_brier,
                "n_evaluated": (harness.get("metrics") or {}).get("n_evaluated"),
            },
            "weather_120d_sidecar": {"mean_brier_score": sidecar_brier, "gate": "mean_brier < 0.05"},
            "weather_120d_stub": {"mean_brier_score": stub_brier, "gate": "mean_brier ≈ 0.25"},
        },
        "artifacts": {
            "harness": str(HARNESS_OUT),
            "brier_prod": str(BRIER_PROD),
            "weather_sidecar": str(WEATHER_SIDECAR),
            "weather_stub": str(WEATHER_STUB),
        },
        "note": "Brier/ECE shadow calibration only; NOT prophecy accuracy or Track A KPI",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_oracle_general_prophecy_brier_shadow_p18_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest oracle general_prophecy brier shadow p18")

    print(
        f"chain_pass=true harness_pass=true prod_mean_brier={prod_brier} "
        f"sidecar_mean_brier={sidecar_brier} stub_mean_brier={stub_brier}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
