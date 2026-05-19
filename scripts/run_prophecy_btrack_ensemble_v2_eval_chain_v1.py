#!/usr/bin/env python3
"""Compare recommended eval: frozen v1 hypothesis vs per-date ensemble v2 directions.

1. Baseline: standard recommended chain (frozen hypothesis direction on score panel).
2. V2 lane: build per-date v2 directions → score with --per-date-direction-json →
   walk-forward with source-direction + expanded prior features.

Writes:
  reports/btrack_ensemble_v2_eval_chain_baseline_v1_latest.json (summary)
  reports/btrack_ensemble_v2_eval_chain_v2_lane_v1_latest.json (summary)
  reports/btrack_ensemble_v2_wf_compare_v1_latest.json (lens/instrument means)

B-track / research_only — does not enable live trading.
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
BUILD_DIRS = ROOT / "scripts" / "build_btrack_ensemble_per_date_directions_v1.py"
REC_CHAIN = ROOT / "scripts" / "run_prophecy_btrack_recommended_eval_chain_v1.py"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_SCORE_REF = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_V2_DIRS = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
DEFAULT_COMPARE = ROOT / "reports/btrack_ensemble_v2_wf_compare_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _gate_mean(doc: dict[str, Any] | None, *, track: str, gate_id: str) -> float | None:
    if not isinstance(doc, dict):
        return None
    tr = doc.get("tracks") or {}
    block = tr.get(track) if isinstance(tr, dict) else None
    if not isinstance(block, dict):
        return None
    gates = block.get("gates")
    if not isinstance(gates, list):
        return None
    for g in gates:
        if isinstance(g, dict) and g.get("gate_id") == gate_id:
            obs = g.get("observed") or {}
            if isinstance(obs, dict):
                v = obs.get("mean_test_accuracy")
                if isinstance(v, (int, float)):
                    return float(v)
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPO)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--score-ref-json", type=Path, default=DEFAULT_SCORE_REF)
    ap.add_argument("--per-date-v2-json", type=Path, default=DEFAULT_V2_DIRS)
    ap.add_argument(
        "--skip-per-date-v2-rebuild",
        action="store_true",
        help="Do not run build_btrack_ensemble_per_date_directions_v1.py; use existing --per-date-v2-json as-is.",
    )
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument("--skip-v2-lane", action="store_true")
    ap.add_argument(
        "--instrument-force-panel-policy",
        action="store_true",
        help="Force instrument WF to use panel predicted_direction (usually hurts dual-leg; opt-in only).",
    )
    ap.add_argument(
        "--instrument-btc-policies",
        default="prior,panel",
        help="Forwarded to recommended chain --instrument-btc-policies (default prior,panel for v2 adaptive WF).",
    )
    ap.add_argument(
        "--per-date-min-confidence",
        type=float,
        default=0.08,
        help="Forwarded to recommended chain --per-date-min-confidence.",
    )
    ap.add_argument(
        "--instrument-include-panel-kospi-mode",
        action="store_true",
        help="Forwarded to recommended chain --instrument-include-panel-kospi-mode.",
    )
    ap.add_argument("--compare-out", type=Path, default=DEFAULT_COMPARE)
    args = ap.parse_args(argv)

    reports = ROOT / "reports"
    baseline_gates = reports / "prophecy_promotion_gates_ensemble_v2_baseline_v1_latest.json"
    v2_gates = reports / "prophecy_promotion_gates_ensemble_v2_lane_v1_latest.json"
    baseline_summary = reports / "btrack_ensemble_v2_eval_baseline_summary_v1_latest.json"
    v2_summary = reports / "btrack_ensemble_v2_eval_v2_lane_summary_v1_latest.json"

    # Per-date v2 direction map (causal price + static bundle lenses)
    if not args.skip_v2_lane and not args.skip_per_date_v2_rebuild:
        rc_dirs = _run(
            [
                sys.executable,
                str(BUILD_DIRS),
                "--bundle-json",
                str(args.bundle_json),
                "--ensemble-config",
                str(args.ensemble_config),
                "--btc-csv",
                str(args.btc_csv),
                "--kospi-csv",
                str(DEFAULT_KOSPI),
                "--recent-trading-days",
                str(args.recent_trading_days),
                "--ensemble-mode",
                "v2_confidence_fusion",
                "--output",
                str(args.per_date_v2_json),
            ]
        )
        if rc_dirs != 0:
            return rc_dirs

    baseline_gates_payload: dict[str, Any] | None = None
    v2_gates_payload: dict[str, Any] | None = None

    if not args.skip_baseline:
        cmd_b = [
            sys.executable,
            str(REC_CHAIN),
            "--recent-trading-days",
            str(args.recent_trading_days),
            "--neutral-bps",
            str(args.neutral_bps),
            "--n-folds",
            str(args.n_folds),
            "--hypothesis-json",
            str(args.hypothesis_json),
            "--btc-csv",
            str(args.btc_csv),
            "--score-json",
            str(reports / "btrack_prophecy_score_ensemble_v2_baseline_v1_latest.json"),
            "--lens-walkforward-out",
            str(reports / "prophecy_per_date_combo_walkforward_ensemble_v2_baseline_v1_latest.json"),
            "--instrument-walkforward-out",
            str(reports / "prophecy_instrument_combo_walkforward_ensemble_v2_baseline_v1_latest.json"),
            "--gates-out",
            str(baseline_gates),
            "--summary-out",
            str(baseline_summary),
            "--calibration-note",
            "ensemble_v2_eval_chain baseline frozen hypothesis",
        ]
        if _run(cmd_b) != 0:
            return 1
        baseline_gates_payload = _load(baseline_gates)

    if not args.skip_v2_lane:
        cmd_v2 = [
            sys.executable,
            str(REC_CHAIN),
            "--recent-trading-days",
            str(args.recent_trading_days),
            "--neutral-bps",
            str(args.neutral_bps),
            "--n-folds",
            str(args.n_folds),
            "--hypothesis-json",
            str(args.hypothesis_json),
            "--btc-csv",
            str(args.btc_csv),
            "--score-json",
            str(reports / "btrack_prophecy_score_ensemble_v2_lane_v1_latest.json"),
            "--lens-walkforward-out",
            str(reports / "prophecy_per_date_combo_walkforward_ensemble_v2_lane_v1_latest.json"),
            "--instrument-walkforward-out",
            str(reports / "prophecy_instrument_combo_walkforward_ensemble_v2_lane_v1_latest.json"),
            "--gates-out",
            str(v2_gates),
            "--summary-out",
            str(v2_summary),
            "--per-date-direction-json",
            str(args.per_date_v2_json),
            "--include-source-direction-signal",
            "--include-expanded-prior-features",
            "--instrument-btc-policies",
            str(args.instrument_btc_policies),
            "--per-date-min-confidence",
            str(float(args.per_date_min_confidence)),
            "--calibration-note",
            "ensemble_v2_eval_chain v2 per-date directions"
            + (" + force-panel instrument" if args.instrument_force_panel_policy else ""),
        ]
        cmd_v2.append("--instrument-include-panel-kospi-mode")
        if not args.instrument_force_panel_policy:
            cmd_v2.extend(
                [
                    "--instrument-adaptive-panel-or-joint",
                    "--instrument-train-holdout-select",
                    "--instrument-beat-bull-train-weight",
                    "0.05",
                ]
            )
        if args.instrument_force_panel_policy:
            cmd_v2.append("--instrument-force-panel-policy")
        if _run(cmd_v2) != 0:
            return 1
        v2_gates_payload = _load(v2_gates)

    compare = {
        "schema": "btrack_ensemble_v2_wf_compare_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc_now(),
        "neutral_bps": float(args.neutral_bps),
        "recent_trading_days": int(args.recent_trading_days),
        "per_date_v2_json": str(args.per_date_v2_json),
        "lanes": {
            "baseline_frozen_hypothesis": {
                "gates_json": str(baseline_gates),
                "lens_mean_test_accuracy": _gate_mean(
                    baseline_gates_payload, track="per_date_lens", gate_id="lens_wf_mean_test_accuracy"
                ),
                "instrument_mean_test_accuracy": _gate_mean(
                    baseline_gates_payload, track="instrument_combo", gate_id="instrument_wf_mean_test_accuracy"
                ),
                "combined_all_passed": baseline_gates_payload.get("combined_all_passed")
                if baseline_gates_payload
                else None,
            },
            "v2_per_date_directions": {
                "gates_json": str(v2_gates),
                "lens_mean_test_accuracy": _gate_mean(
                    v2_gates_payload, track="per_date_lens", gate_id="lens_wf_mean_test_accuracy"
                ),
                "instrument_mean_test_accuracy": _gate_mean(
                    v2_gates_payload, track="instrument_combo", gate_id="instrument_wf_mean_test_accuracy"
                ),
                "combined_all_passed": v2_gates_payload.get("combined_all_passed") if v2_gates_payload else None,
            },
        },
        "note": "WF 0.55 strict promotion unchanged; compare lane means only.",
    }
    args.compare_out.parent.mkdir(parents=True, exist_ok=True)
    args.compare_out.write_text(json.dumps(compare, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.compare_out.resolve()}")
    bl = compare["lanes"]["baseline_frozen_hypothesis"]
    v2 = compare["lanes"]["v2_per_date_directions"]
    print(
        f"baseline lens={bl.get('lens_mean_test_accuracy')} inst={bl.get('instrument_mean_test_accuracy')} | "
        f"v2 lens={v2.get('lens_mean_test_accuracy')} inst={v2.get('instrument_mean_test_accuracy')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
