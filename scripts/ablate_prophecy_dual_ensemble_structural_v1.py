# @MKM12-METADATA
# Type: Logic
# Purpose: Dual ensemble v1 vs v2_confidence_fusion structural ablation (B-track)
# Keywords: prophecy, ensemble, dual, structural, research_only
#!/usr/bin/env python3
"""Compare dual per-date ensemble v1 vs v2_confidence_fusion on recommended eval lane.

Baseline metrics are read from existing recommended *_latest.json (no rerun).
V2 lane: build 180d dual directions with v2_confidence_fusion → isolated recommended chain.

B-track / [HYPO] / research_only — does not change production defaults automatically.
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
DUAL_BUILD = ROOT / "scripts" / "build_btrack_dual_per_date_directions_v1.py"
REC_CHAIN = ROOT / "scripts" / "run_prophecy_btrack_recommended_eval_chain_v1.py"
HIT_EVAL = ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"

BASELINE_LENS = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
BASELINE_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
BASELINE_GATES = ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json"

DEFAULT_V2_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v2_structural_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_dual_ensemble_structural_ablation_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _lane_summary(
    *,
    label: str,
    lens_path: Path,
    score_path: Path,
    gates_path: Path,
    reports_dir: Path,
) -> dict[str, Any]:
    lens = _load(lens_path) or {}
    gates = _load(gates_path) or {}
    agg = lens.get("aggregate") if isinstance(lens.get("aggregate"), dict) else {}
    hit_doc = None
    hit_path = score_path.parent / f"prophecy_hit_rate_eval_{score_path.stem}_run_latest.json"
    hit_doc = _load(hit_path) if hit_path.is_file() else None
    if hit_doc is None and label == "baseline_v1_regime_adaptive":
        hit_doc = _load(reports_dir / "prophecy_hit_rate_eval_recommended_chain_run_latest.json")
    pooled_hit = None
    kospi_hit = None
    btc_hit = None
    if isinstance(hit_doc, dict):
        metrics = hit_doc.get("metrics") if isinstance(hit_doc.get("metrics"), dict) else {}
        pooled_hit = metrics.get("price_directional_hit_rate")
        legs = hit_doc.get("legs") if isinstance(hit_doc.get("legs"), dict) else {}
        pooled = hit_doc.get("pooled") if isinstance(hit_doc.get("pooled"), dict) else {}
        if pooled_hit is None and pooled:
            pooled_hit = pooled.get("price_directional_hit_rate")
        if isinstance(legs.get("kospi"), dict):
            kospi_hit = legs["kospi"].get("price_directional_hit_rate")
        if isinstance(legs.get("btc"), dict):
            btc_hit = legs["btc"].get("price_directional_hit_rate")
    return {
        "lane_id": label,
        "lens_walkforward_json": str(lens_path),
        "score_json": str(score_path),
        "gates_json": str(gates_path),
        "mean_test_accuracy": agg.get("mean_test_accuracy"),
        "fraction_test_beats_always_bull_gt": agg.get("fraction_test_beats_always_bull"),
        "fraction_test_meets_or_beats_always_bull_gte": agg.get("fraction_test_meets_or_beats_always_bull"),
        "combined_all_passed": gates.get("combined_all_passed"),
        "pooled_hit_rate": pooled_hit,
        "kospi_hit_rate": kospi_hit,
        "btc_hit_rate": btc_hit,
    }


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Dual ensemble structural ablation (v1 baseline vs v2).")
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--v2-dual-json", type=Path, default=DEFAULT_V2_DUAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-v2-lane", action="store_true")
    args = ap.parse_args()

    reports = ROOT / "reports"
    v2_score = reports / "btrack_prophecy_score_dual_v2_structural_v1_latest.json"
    v2_lens = reports / "prophecy_per_date_combo_walkforward_dual_v2_structural_v1_latest.json"
    v2_inst = reports / "prophecy_instrument_combo_walkforward_dual_v2_structural_v1_latest.json"
    v2_gates = reports / "prophecy_promotion_gates_dual_v2_structural_v1_latest.json"
    v2_summary = reports / "prophecy_btrack_dual_v2_structural_eval_summary_v1_latest.json"
    v2_hit = reports / "prophecy_hit_rate_eval_dual_v2_structural_v1_latest.json"

    baseline = _lane_summary(
        label="baseline_v1_regime_adaptive",
        lens_path=BASELINE_LENS,
        score_path=BASELINE_SCORE,
        gates_path=BASELINE_GATES,
        reports_dir=reports,
    )
    if baseline.get("mean_test_accuracy") is None:
        print(f"Missing baseline lens WF: {BASELINE_LENS}", file=sys.stderr)
        return 2

    lanes: list[dict[str, Any]] = [baseline]
    rc = 0

    if not args.skip_v2_lane:
        build_cmd = [
            sys.executable,
            str(DUAL_BUILD),
            "--recent-trading-days",
            str(int(args.recent_trading_days)),
            "--ensemble-mode",
            "v2_confidence_fusion",
            "--dual-output",
            str(args.v2_dual_json),
            "--skip-btc-legacy-output",
        ]
        rc = _run(build_cmd)
        if rc != 0:
            print("dual v2 build failed", file=sys.stderr)
            return rc

        rec_cmd = [
            sys.executable,
            str(REC_CHAIN),
            "--recent-trading-days",
            str(int(args.recent_trading_days)),
            "--neutral-bps",
            str(float(args.neutral_bps)),
            "--n-folds",
            str(int(args.n_folds)),
            "--per-date-direction-json",
            str(args.v2_dual_json),
            "--score-json",
            str(v2_score),
            "--lens-walkforward-out",
            str(v2_lens),
            "--instrument-walkforward-out",
            str(v2_inst),
            "--gates-out",
            str(v2_gates),
            "--summary-out",
            str(v2_summary),
            "--calibration-note",
            "dual_ensemble_v2_confidence_fusion_structural_ablation_v1",
        ]
        rc = _run(rec_cmd)
        if rc != 0:
            print("v2 recommended chain failed", file=sys.stderr)
            return rc

        hit_cmd = [
            sys.executable,
            str(HIT_EVAL),
            "--run-mode",
            "price",
            "--score-json",
            str(v2_score),
            "--output",
            str(v2_hit),
        ]
        _run(hit_cmd)

        v2_lane = _lane_summary(
            label="v2_confidence_fusion_per_date",
            lens_path=v2_lens,
            score_path=v2_score,
            gates_path=v2_gates,
            reports_dir=reports,
        )
        v2_lane_hit = _load(v2_hit)
        if isinstance(v2_lane_hit, dict):
            metrics = v2_lane_hit.get("metrics") if isinstance(v2_lane_hit.get("metrics"), dict) else {}
            v2_lane["pooled_hit_rate"] = metrics.get("price_directional_hit_rate")
        lanes.append(v2_lane)

    def _rank(r: dict[str, Any]) -> tuple[float, float, float]:
        return (
            float(r.get("mean_test_accuracy") or 0.0),
            float(r.get("pooled_hit_rate") or 0.0),
            float(r.get("fraction_test_meets_or_beats_always_bull_gte") or 0.0),
        )

    best = max(lanes, key=_rank) if lanes else None
    payload: dict[str, Any] = {
        "schema": "prophecy_dual_ensemble_structural_ablation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "recent_trading_days": int(args.recent_trading_days),
            "neutral_bps": float(args.neutral_bps),
            "baseline_note": "v1 dual rebuild inside recommended chain; regime-adaptive KOSPI lens",
            "v2_note": "v2_confidence_fusion per-date directions fed to score panel",
        },
        "lanes": lanes,
        "best_by_mean_then_pooled_hit": best,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}", flush=True)
    if best:
        print(
            f"best={best.get('lane_id')} mean={best.get('mean_test_accuracy')} "
            f"pooled={best.get('pooled_hit_rate')} gt={best.get('fraction_test_beats_always_bull_gt')}",
            flush=True,
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
