#!/usr/bin/env python3
"""[HYPO] One-click: V2 dual-axis strict promotion profile (repro SSOT).

Winning measurement contract (2026-05-19, Fact-Lock):
  - 180d recommended eval, neutral_bps=0.4
  - per-date v2_confidence_fusion directions (ensemble default price_lookback_days=5)
  - --include-source-direction-signal ON
  - --include-expanded-prior-features OFF (regresses lens WF ~48% vs ~56%)
  - mild_downside block ON (recommended chain default)

Optional ``--run-promotion-bundle``: streak 5 + evidence pack on same WF artifacts
(``Run-BtrackEnsembleV2PromotionBundle_v1.ps1 -SkipEvalRun``).

research_only — B-track numeric pass != A-track / live trading (human + ops gates).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD_BUNDLE = ROOT / "scripts/build_btrack_llm_input_bundle.py"
BUILD_DIRS = ROOT / "scripts/build_btrack_ensemble_per_date_directions_v1.py"
REC = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
PROMO_PS1 = ROOT / "scripts/Run-BtrackEnsembleV2PromotionBundle_v1.ps1"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DIRS_OUT = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
GATES_OUT = ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json"
GATES_ART = ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
OUT = ROOT / "reports/btrack_lens_v2_dual_strict_promotion_chain_v1_latest.json"
CALIBRATION = (
    "btrack_lens_v2_dual_strict_v1: v2 per-date + source_signal; expanded_prior OFF; nbps=0.4"
)


def _run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def _gate_means(gates: dict[str, Any]) -> tuple[float | None, float | None]:
    tracks = gates.get("tracks") if isinstance(gates.get("tracks"), dict) else {}
    lens = tracks.get("per_date_lens") if isinstance(tracks, dict) else {}
    inst = tracks.get("instrument_combo") if isinstance(tracks, dict) else {}
    lm = im = None

    def _mean(block: dict) -> float | None:
        for g in block.get("gates") or []:
            if isinstance(g, dict) and g.get("gate_id", "").endswith("mean_test_accuracy"):
                obs = g.get("observed") or {}
                v = obs.get("mean_test_accuracy")
                if isinstance(v, (int, float)):
                    return float(v)
        return None

    if isinstance(lens, dict):
        lm = _mean(lens)
    if isinstance(inst, dict):
        im = _mean(inst)
    return lm, im


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--neutral-bps", type=float, default=0.4)
    ap.add_argument("--skip-bundle", action="store_true")
    ap.add_argument("--skip-directions-rebuild", action="store_true")
    ap.add_argument("--run-promotion-bundle", action="store_true")
    ap.add_argument("--streak-target", type=int, default=5)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_bundle:
        rc = _run([sys.executable, str(BUILD_BUNDLE)])
        steps.append({"step": "build_llm_input_bundle", "rc": rc})
        if rc != 0:
            _write_out(steps, None)
            return rc

    if not args.skip_directions_rebuild:
        rc = _run(
            [
                sys.executable,
                str(BUILD_DIRS),
                "--recent-trading-days",
                str(args.recent_trading_days),
                "--ensemble-config",
                str(DEFAULT_CFG),
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
        steps.append({"step": "build_per_date_v2_directions", "rc": rc, "ensemble_config": str(DEFAULT_CFG)})
        if rc != 0:
            _write_out(steps, None)
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
            "--instrument-beat-bull-train-weight",
            "0.05",
            "--gates-out",
            str(GATES_OUT),
            "--score-json",
            str(ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"),
            "--lens-walkforward-out",
            str(ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"),
            "--instrument-walkforward-out",
            str(ROOT / "reports/prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json"),
            "--summary-out",
            str(ROOT / "reports/prophecy_btrack_recommended_eval_chain_summary_v1_latest.json"),
            "--calibration-note",
            CALIBRATION,
        ]
    )
    steps.append({"step": "recommended_eval_chain", "rc": rc})

    gates: dict[str, Any] = {}
    if GATES_OUT.is_file():
        try:
            gates = json.loads(GATES_OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            gates = {}

    if gates.get("combined_all_passed") and GATES_OUT.is_file():
        GATES_ART.parent.mkdir(parents=True, exist_ok=True)
        GATES_ART.write_text(GATES_OUT.read_text(encoding="utf-8"), encoding="utf-8")

    promo_rc: int | None = None
    if args.run_promotion_bundle and gates.get("combined_all_passed") and PROMO_PS1.is_file():
        promo_rc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(PROMO_PS1),
                "-SkipEvalRun",
                "-StreakTarget",
                str(max(1, int(args.streak_target))),
            ],
            cwd=str(ROOT),
        ).returncode
        steps.append({"step": "promotion_bundle", "rc": promo_rc})
        if promo_rc != 0:
            _write_out(steps, gates)
            return promo_rc
        if GATES_OUT.is_file():
            try:
                gates = json.loads(GATES_OUT.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

    _write_out(steps, gates)
    ok = bool(gates.get("combined_all_passed"))
    if args.run_promotion_bundle:
        ok = ok and bool(gates.get("auto_promote_ready"))
    return 0 if ok else 1


def _write_out(steps: list[dict], gates: dict[str, Any] | None) -> None:
    g = gates or {}
    lm, im = _gate_means(g)
    doc = {
        "schema": "btrack_lens_v2_dual_strict_promotion_chain_v1",
        "profile": {
            "neutral_bps": 0.4,
            "include_source_direction_signal": True,
            "include_expanded_prior_features": False,
            "ensemble_mode": "v2_confidence_fusion",
            "price_lookback_days": 5,
            "calibration_note": CALIBRATION,
        },
        "steps": steps,
        "lens_mean_test_accuracy": lm,
        "instrument_mean_test_accuracy": im,
        "combined_all_passed": g.get("combined_all_passed"),
        "strict_passed": g.get("strict_passed"),
        "strict_pass_streak": g.get("strict_pass_streak"),
        "auto_promote_ready": g.get("auto_promote_ready"),
        "gates_json": str(GATES_OUT.relative_to(ROOT)).replace("\\", "/"),
        "gates_artifacts_json": str(GATES_ART.relative_to(ROOT)).replace("\\", "/"),
        "evidence_pack_json": "docs/final/artifacts/prophecy_gate_evidence_pack_v1_latest.json",
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUT}")
    print(
        f"lens={lm} inst={im} combined={g.get('combined_all_passed')} "
        f"streak={g.get('strict_pass_streak')} auto_promote_ready={g.get('auto_promote_ready')}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
