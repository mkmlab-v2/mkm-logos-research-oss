#!/usr/bin/env python3
"""[HYPO] V2 feature refresh: rebuild LLM bundle → per-date v2 directions → strict recommended eval.

Aligns instrument WF flags with ``run_prophecy_btrack_ensemble_v2_eval_chain_v1.py`` v2 lane.
research_only — no live trading or threshold relaxation.
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_BUNDLE = ROOT / "scripts/build_btrack_llm_input_bundle.py"
BUILD_DIRS = ROOT / "scripts/build_btrack_ensemble_per_date_directions_v1.py"
REC = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DIRS_OUT = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
GATES_OUT = ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json"
SUMMARY_OUT = ROOT / "reports/btrack_lens_v2_feature_refresh_chain_v1_latest.json"


def _deep_merge(base: dict, patch: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--neutral-bps", type=float, default=0.4)
    ap.add_argument(
        "--price-lookback-days",
        type=int,
        default=5,
        help="Ensemble price_lookback_days override (dual-strict SSOT uses 5 from btrack_lens_ensemble_v1.json).",
    )
    ap.add_argument("--skip-bundle", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_bundle:
        rc = _run([sys.executable, str(BUILD_BUNDLE)])
        steps.append({"step": "build_llm_input_bundle", "rc": rc})
        if rc != 0:
            _write_summary(steps, None)
            return rc

    cfg = json.loads(DEFAULT_CFG.read_text(encoding="utf-8"))
    cfg = _deep_merge(
        cfg,
        {
            "rules": {
                "ensemble_mode": "v2_confidence_fusion",
                "price_lookback_days": int(args.price_lookback_days),
            }
        },
    )
    cfg_path = ROOT / "reports/btrack_lens_v2_feature_refresh_ensemble_cfg.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    rc = _run(
        [
            sys.executable,
            str(BUILD_DIRS),
            "--recent-trading-days",
            str(args.recent_trading_days),
            "--ensemble-config",
            str(cfg_path),
            "--bundle-json",
            str(DEFAULT_BUNDLE),
            "--btc-csv",
            str(DEFAULT_BTC),
            "--kospi-csv",
            str(DEFAULT_KOSPI),
            "--ensemble-mode",
            "v2_confidence_fusion",
            "--output",
            str(DIRS_OUT),
        ]
    )
    steps.append({"step": "build_per_date_v2_directions", "rc": rc, "ensemble_config": str(cfg_path)})
    if rc != 0:
        _write_summary(steps, None)
        return rc

    rc = _run(
        [
            sys.executable,
            str(REC),
            "--recent-trading-days",
            str(args.recent_trading_days),
            "--neutral-bps",
            str(float(args.neutral_bps)),
            "--per-date-direction-json",
            str(DIRS_OUT),
            "--include-source-direction-signal",
            "--gates-out",
            str(GATES_OUT),
            "--score-json",
            str(ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"),
            "--lens-walkforward-out",
            str(ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"),
            "--instrument-walkforward-out",
            str(ROOT / "reports/prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json"),
            "--calibration-note",
            "lens_v2_feature_refresh_chain_v1",
        ]
    )
    steps.append({"step": "recommended_eval_chain", "rc": rc})

    gates = {}
    if GATES_OUT.is_file():
        try:
            gates = json.loads(GATES_OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            gates = {}
    _write_summary(steps, gates)
    return 0 if gates.get("combined_all_passed") else 1


def _write_summary(steps: list[dict], gates: dict | None) -> None:
    doc = {
        "schema": "btrack_lens_v2_feature_refresh_chain_v1",
        "steps": steps,
        "combined_all_passed": (gates or {}).get("combined_all_passed"),
        "strict_passed": (gates or {}).get("strict_passed"),
        "gates_json": str(GATES_OUT.relative_to(ROOT)).replace("\\", "/"),
    }
    SUMMARY_OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {SUMMARY_OUT}")


if __name__ == "__main__":
    raise SystemExit(main())
