#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full v2 sandbox + market_sasang_lens bridge + upstream compare summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/market_psych_v2_lens_integration_chain_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/market_psych_v2_lens_integration_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--psych-days", type=int, default=400)
    ap.add_argument("--skip-ablation", action="store_true")
    ap.add_argument(
        "--include-manifest-holdout-sweep",
        action="store_true",
        help="Phase 4: train-select manifest weight grid (holdout report only).",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    def step(name: str, cmd: list[str]) -> bool:
        rc = _run(cmd)
        steps.append({"step": name, "exit_code": rc})
        return rc == 0

    ok = step(
        "psych_v2_csv",
        [sys.executable, "scripts/build_market_psychology_kospi_from_yfinance_v2.py", "--days", str(args.psych_days)],
    )
    if not ok:
        return 2
    step("map_v2", [sys.executable, "scripts/map_market_psych_to_sasang_axis_v2.py"])
    step("per_date_v2", [sys.executable, "scripts/build_btrack_per_date_directions_market_psych_v2.py"])
    step("lens_v2_bridge", [sys.executable, "scripts/run_market_sasang_lens_from_market_psych_v2_v1.py"])
    if not args.skip_ablation:
        step(
            "v1_v2_ablation",
            [sys.executable, "scripts/run_market_psych_v1_vs_v2_price_ablation_v1.py", "--skip-yfinance"],
        )
    if args.include_manifest_holdout_sweep:
        step(
            "manifest_holdout_sweep",
            [sys.executable, "scripts/sweep_market_psych_manifest_holdout_v1.py"],
        )
        step(
            "manifest_candidate_price_validation",
            [
                sys.executable,
                "scripts/run_market_psych_manifest_candidate_price_validation_v1.py",
                "--skip-yfinance",
            ],
        )

    ablation = None
    p = ROOT / "reports/market_psych_v1_vs_v2_price_ablation_v1_latest.json"
    if p.is_file():
        ablation = json.loads(p.read_text(encoding="utf-8"))
    compare = None
    c = ROOT / "reports/market_sasang_lens_upstream_vs_v2_bridge_v1_latest.json"
    if c.is_file():
        compare = json.loads(c.read_text(encoding="utf-8"))

    doc = {
        "schema": "market_psych_v2_lens_integration_chain_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "not_promoted_track_a": True,
        "pipeline_steps": steps,
        "artifacts": {
            "psych_v2_csv": "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv",
            "axis_map_v2": "reports/market_psych_sasang_axis_map_v2_latest.json",
            "per_date_v2": "reports/btrack_per_date_directions_market_psych_v2.json",
            "market_sasang_lens_v2": "docs/final/artifacts/market_sasang_lens_from_market_psych_v2_latest.json",
            "lens_compare": "reports/market_sasang_lens_upstream_vs_v2_bridge_v1_latest.json",
            "price_ablation": "reports/market_psych_v1_vs_v2_price_ablation_v1_latest.json",
            "manifest_holdout_sweep": "reports/market_psych_manifest_holdout_sweep_v1_latest.json",
        },
        "price_ablation_delta": (ablation or {}).get("delta_v2_minus_v1"),
        "manifest_holdout_best": (
            json.loads(
                (ROOT / "reports/market_psych_manifest_holdout_sweep_v1_latest.json").read_text(
                    encoding="utf-8"
                )
            ).get("best_on_train")
            if (ROOT / "reports/market_psych_manifest_holdout_sweep_v1_latest.json").is_file()
            else None
        ),
        "lens_softmax_compare": {
            "legacy": (compare or {}).get("state_vector_legacy"),
            "v2_bridge": (compare or {}).get("state_vector_v2_bridge"),
        },
        "verdict_ko": (
            "v2 psych → machine_readables → market_sasang_lens bridge 연결 완료. "
            "가격 ablation은 별도 JSON. Track A·실매매 합선 금지."
        ),
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(text, encoding="utf-8")
    print(str(args.out.resolve()))
    return 0 if all(s["exit_code"] == 0 for s in steps) else 2


if __name__ == "__main__":
    raise SystemExit(main())
