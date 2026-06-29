#!/usr/bin/env python3
"""Phase 1 protocol harmonization — recommended chain @ 252d/5bps vs RQ-025 SSOT [HYPO].

Runs measurement-only recommended eval (isolated paths) and emits compare artifact.
Does not promote Track A or overwrite default 2bps/180d latest chain outputs.
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHAIN = ROOT / "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py"
DIR = ROOT / "reports/prophecy_protocol_harmonization_phase1_v1"
DEFAULT_OUT = ROOT / "reports/prophecy_protocol_harmonization_phase1_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/prophecy_protocol_harmonization_phase1_v1_latest.json"

RQ025_HOLDOUT = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
RQ025_TSFM = ROOT / "reports/rq025_tsfm_delta_arms_v1_latest.json"
FABBA_SHADOW = ROOT / "reports/prophecy_fabba_sidecar_wf_shadow_v1_latest.json"
BASELINE_LENS = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
BASELINE_INST = ROOT / "reports/prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json"
BASELINE_GATES = ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json"

SCHEMA = "prophecy_protocol_harmonization_phase1_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _wf_agg(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    agg = doc.get("aggregate") or {}
    inputs = doc.get("inputs") or {}
    return {
        "artifact": _rel(path),
        "present": path.is_file(),
        "mean_test_accuracy": agg.get("mean_test_accuracy"),
        "stdev_test_accuracy": agg.get("stdev_test_accuracy"),
        "min_test_accuracy": agg.get("min_test_accuracy"),
        "max_test_accuracy": agg.get("max_test_accuracy"),
        "fraction_test_beats_always_bull": agg.get("fraction_test_beats_always_bull"),
        "n_rows": inputs.get("n_rows_after_target_filter") or inputs.get("n_distinct_eval_dates"),
        "neutral_bps": inputs.get("neutral_bps"),
    }


def _rq025_kospi_ensemble_5bps(holdout: dict[str, Any]) -> dict[str, Any]:
    win = holdout.get("window") or {}
    arms = ((holdout.get("blocked_walkforward_test_only") or {}).get("arms") or [])
    ens = next((a for a in arms if a.get("arm_id") == "per_date_kospi_ensemble"), {})
    mom = next((a for a in arms if a.get("arm_id") == "mom_20d"), {})
    return {
        "protocol": "kospi_only_252d_blocked_wf",
        "neutral_bps": win.get("neutral_bps"),
        "eval_days": win.get("eval_days"),
        "per_date_kospi_ensemble_pooled_hr": ens.get("pooled_test_directional_hit_rate"),
        "per_date_kospi_ensemble_mean_hr": ens.get("mean_test_directional_hit_rate"),
        "mom_20d_pooled_hr": mom.get("pooled_test_directional_hit_rate"),
        "wf_majority_pooled_hr": (holdout.get("best_pooled_arm") or {}).get(
            "pooled_test_directional_hit_rate"
        ),
        "artifact": _rel(RQ025_HOLDOUT),
    }


def _rq025_tsfm_arms(tsfm: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm in tsfm.get("arms") or []:
        if not isinstance(arm, dict):
            continue
        hr = (
            arm.get("pooled_test_hr")
            or arm.get("chronos2_pooled_test_hr")
            or arm.get("timesfm_pooled_test_hr")
            or arm.get("moirai2_pooled_test_hr")
        )
        if hr is None and arm.get("arm_id") != "moirai2_quantile_shadow":
            continue
        rows.append(
            {
                "arm_id": arm.get("arm_id"),
                "pooled_test_hr": hr,
                "protocol_note": arm.get("protocol") or arm.get("note_ko"),
                "evidence": arm.get("evidence"),
            }
        )
    return rows


def _fabba_kospi_5bps(fabba: dict[str, Any]) -> dict[str, Any] | None:
    for panel in fabba.get("panels") or []:
        if panel.get("instrument_id") != "kospi":
            continue
        for run in panel.get("neutral_bps_runs") or []:
            if float(run.get("neutral_bps") or 0) != 5.0:
                continue
            sidecar = next(
                (a for a in (run.get("arms") or []) if a.get("arm_id") == "fabba_sidecar_last_slope"),
                {},
            )
            mom = next((a for a in (run.get("arms") or []) if a.get("arm_id") == "mom_20d"), {})
            return {
                "fabba_sidecar_pooled_hr": sidecar.get("pooled_test_directional_hit_rate"),
                "mom_20d_pooled_hr": mom.get("pooled_test_directional_hit_rate"),
                "eval_days": (panel.get("window") or {}).get("eval_days"),
            }
    return None


def run_chain(
    *,
    neutral_bps: float,
    recent_trading_days: int,
    n_folds: int,
    skip_gates: bool,
) -> tuple[int, dict[str, Path]]:
    DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "score": DIR / "score_252d_5bps.json",
        "lens": DIR / "lens_walkforward_252d_5bps.json",
        "inst": DIR / "instrument_walkforward_252d_5bps.json",
        "gates": DIR / "promotion_gates_252d_5bps.json",
        "summary": DIR / "chain_summary_252d_5bps.json",
        "streak": DIR / "streak_252d_5bps.json",
    }
    cmd = [
        sys.executable,
        str(CHAIN),
        "--neutral-bps",
        str(neutral_bps),
        "--recent-trading-days",
        str(recent_trading_days),
        "--n-folds",
        str(n_folds),
        "--score-json",
        str(paths["score"]),
        "--lens-walkforward-out",
        str(paths["lens"]),
        "--instrument-walkforward-out",
        str(paths["inst"]),
        "--gates-out",
        str(paths["gates"]),
        "--summary-out",
        str(paths["summary"]),
        "--streak-history-json",
        str(paths["streak"]),
        "--calibration-note",
        "protocol_harmonization_phase1_v1: 252d/5bps isolated; RQ-025 compare only",
    ]
    if skip_gates:
        cmd.append("--skip-gates")
    rc = subprocess.call(cmd, cwd=str(ROOT))
    return rc, paths


def build_report(
    *,
    chain_paths: dict[str, Path],
    chain_exit_code: int,
    neutral_bps: float,
    recent_trading_days: int,
    n_folds: int,
) -> dict[str, Any]:
    lens_5 = _wf_agg(chain_paths["lens"])
    inst_5 = _wf_agg(chain_paths["inst"])
    gates_5 = _read_json(chain_paths["gates"])
    summary_5 = _read_json(chain_paths["summary"])

    lens_2 = _wf_agg(BASELINE_LENS)
    inst_2 = _wf_agg(BASELINE_INST)
    gates_2 = _read_json(BASELINE_GATES)

    holdout = _read_json(RQ025_HOLDOUT)
    tsfm = _read_json(RQ025_TSFM)
    fabba = _read_json(FABBA_SHADOW)

    rq025_ref = _rq025_kospi_ensemble_5bps(holdout)
    fabba_5 = _fabba_kospi_5bps(fabba)

    lens_5_hr = lens_5.get("mean_test_accuracy")
    inst_5_hr = inst_5.get("mean_test_accuracy")
    rq025_ens = rq025_ref.get("per_date_kospi_ensemble_pooled_hr")
    rq025_majority = rq025_ref.get("wf_majority_pooled_hr")

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "mission_line": "Phase 1 protocol harmonization — dual-leg recommended chain 252d/5bps vs RQ-025 KOSPI table",
        "protocol": {
            "neutral_bps": neutral_bps,
            "recent_trading_days": recent_trading_days,
            "n_folds": n_folds,
            "panel": "dual_leg_kospi_btc",
            "gates_skipped": gates_5 == {},
        },
        "chain_run": {
            "exit_code": chain_exit_code,
            "summary": summary_5,
            "artifacts": {k: _rel(v) for k, v in chain_paths.items()},
        },
        "recommended_chain_252d_5bps": {
            "lens_walkforward_btc_target": lens_5,
            "instrument_combo_walkforward": inst_5,
            "combined_all_passed": gates_5.get("combined_all_passed"),
        },
        "recommended_chain_180d_2bps_baseline": {
            "lens_walkforward": lens_2,
            "instrument_walkforward": inst_2,
            "combined_all_passed": gates_2.get("combined_all_passed"),
            "note_ko": "기존 reports/*_recommended_chain_v1_latest.json — 덮어쓰지 않음",
        },
        "protocol_delta_5bps_252d_minus_2bps_180d_pp": {
            "lens_mean_hr_delta_pp": round((float(lens_5_hr) - float(lens_2.get("mean_test_accuracy"))) * 100, 4)
            if lens_5_hr is not None and lens_2.get("mean_test_accuracy") is not None
            else None,
            "instrument_mean_hr_delta_pp": round(
                (float(inst_5_hr) - float(inst_2.get("mean_test_accuracy"))) * 100, 4
            )
            if inst_5_hr is not None and inst_2.get("mean_test_accuracy") is not None
            else None,
        },
        "rq025_reference_kospi_252d_5bps": rq025_ref,
        "rq025_tsfm_arms_snapshot": _rq025_tsfm_arms(tsfm),
        "fabba_sidecar_kospi_252d_5bps": fabba_5,
        "cross_protocol_compare_pp": {
            "lens_5bps_dual_leg_vs_rq025_ensemble_pooled": round(
                (float(lens_5_hr) - float(rq025_ens)) * 100, 4
            )
            if lens_5_hr is not None and rq025_ens is not None
            else None,
            "instrument_5bps_dual_leg_vs_rq025_ensemble_pooled": round(
                (float(inst_5_hr) - float(rq025_ens)) * 100, 4
            )
            if inst_5_hr is not None and rq025_ens is not None
            else None,
            "instrument_5bps_vs_rq025_majority_pooled": round(
                (float(inst_5_hr) - float(rq025_majority)) * 100, 4
            )
            if inst_5_hr is not None and rq025_majority is not None
            else None,
        },
        "verdict_ko": [
            "프로토콜 상이 시 HR 직접 승격 금지 — dual-leg instrument WF vs KOSPI-only ensemble",
            f"252d/5bps lens mean={lens_5_hr} instrument mean={inst_5_hr}",
            f"RQ-025 ensemble pooled={rq025_ens} majority={rq025_majority}",
            "strict promotion remains false — measurement harmonization only",
        ],
        "ok": chain_paths["lens"].is_file() and chain_paths["inst"].is_file(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--recent-trading-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--skip-chain", action="store_true")
    ap.add_argument("--with-gates", action="store_true", help="Run promotion gates (may exit non-zero).")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    paths = {
        "score": DIR / "score_252d_5bps.json",
        "lens": DIR / "lens_walkforward_252d_5bps.json",
        "inst": DIR / "instrument_walkforward_252d_5bps.json",
        "gates": DIR / "promotion_gates_252d_5bps.json",
        "summary": DIR / "chain_summary_252d_5bps.json",
        "streak": DIR / "streak_252d_5bps.json",
    }
    chain_rc = 0
    if not args.skip_chain:
        chain_rc, paths = run_chain(
            neutral_bps=float(args.neutral_bps),
            recent_trading_days=int(args.recent_trading_days),
            n_folds=int(args.n_folds),
            skip_gates=not bool(args.with_gates),
        )

    payload = build_report(
        chain_paths=paths,
        chain_exit_code=chain_rc,
        neutral_bps=float(args.neutral_bps),
        recent_trading_days=int(args.recent_trading_days),
        n_folds=int(args.n_folds),
    )

    for path in (args.output, args.artifact_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not payload.get("ok"):
        print("FAIL: harmonization artifacts missing", file=sys.stderr)
        return 1
    inst = (payload.get("recommended_chain_252d_5bps") or {}).get("instrument_combo_walkforward") or {}
    rq = payload.get("rq025_reference_kospi_252d_5bps") or {}
    print(
        f"OK phase1 harmonization inst_hr={inst.get('mean_test_accuracy')} "
        f"rq025_ens={rq.get('per_date_kospi_ensemble_pooled_hr')} chain_rc={chain_rc} -> {args.output}"
    )
    return 0 if chain_rc == 0 else chain_rc


if __name__ == "__main__":
    raise SystemExit(main())
