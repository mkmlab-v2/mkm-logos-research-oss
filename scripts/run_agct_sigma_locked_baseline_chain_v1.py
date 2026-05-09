#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


LOCKED_SIGMA = 0.0315
DEFAULT_SIGMA_POLICY_JSON = Path(__file__).resolve().parents[1] / "docs" / "final" / "artifacts" / "agct_sigma_lock_policy_v1.json"
TIE_EPS = 1e-12


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], cwd: Path) -> None:
    t0 = time.perf_counter()
    print(f"[RUN] {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=False, text=True, check=False)
    dt = time.perf_counter() - t0
    if r.returncode != 0:
        raise RuntimeError(f"step_failed returncode={r.returncode} elapsed_sec={dt:.1f}")
    print(f"[DONE] elapsed_sec={dt:.1f}", flush=True)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_locked_sigma(policy_json: Path | None, sigma_override: float | None) -> float:
    if sigma_override is not None:
        return float(sigma_override)
    if policy_json and policy_json.is_file():
        try:
            obj = _read_json(policy_json)
            v = obj.get("locked_sigma")
            if isinstance(v, (int, float)):
                return float(v)
        except Exception:
            pass
    return float(LOCKED_SIGMA)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run locked-sigma baseline chain (B-track).")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--base-seed", type=int, default=20260505)
    ap.add_argument("--batch-gap", type=int, default=1000)
    ap.add_argument("--repro-trials", type=int, default=50)
    ap.add_argument("--repro-batches", type=int, default=3)
    ap.add_argument("--daily-seed", type=int, default=20260505)
    ap.add_argument("--daily-drift-runs", type=int, default=20)
    ap.add_argument("--h2h-trials", type=int, default=50)
    ap.add_argument("--h2h-batches", type=int, default=3)
    ap.add_argument("--h2h-sigmas", type=str, default="0.0315,0.0325")
    ap.add_argument("--locked-sigma", type=float, default=None)
    ap.add_argument("--sigma-policy-json", type=Path, default=DEFAULT_SIGMA_POLICY_JSON)
    ap.add_argument(
        "--market-psych-csv",
        type=Path,
        default=root / "data" / "market_sasang" / "market_psychology_sample_v1.csv",
    )
    ap.add_argument("--sasang-dna-weight", type=float, default=0.6)
    ap.add_argument("--sasang-market-weight", type=float, default=0.4)
    ap.add_argument("--alert-go-rate-min", type=float, default=0.25)
    ap.add_argument("--alert-transition-intensity-min", type=float, default=0.40)
    ap.add_argument("--min-trials-for-hard-enforcement", type=int, default=5)
    ap.add_argument("--run-regression-check", action="store_true")
    ap.add_argument("--strict-regression-check", action="store_true")
    ap.add_argument(
        "--regression-baseline-json",
        type=Path,
        default=root / "reports" / "agct_sigma_locked_baseline_chain_v1_run1.json",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sigma_locked_baseline_chain_v1_latest.json",
    )
    ns = ap.parse_args()
    locked_sigma = _resolve_locked_sigma(ns.sigma_policy_json, ns.locked_sigma)

    repro_script = root / "scripts" / "run_agct_sigma_fixed_repro_3batch_v1.py"
    daily_script = root / "scripts" / "run_agct_daily_formula_drift_chain_v1.py"
    h2h_script = root / "scripts" / "run_agct_sigma_head_to_head_3batch_v1.py"
    sasang_reasoning_script = root / "scripts" / "run_sasang_dna_market_reasoning_v1.py"
    coordinator_script = root / "scripts" / "run_mkm_global_coordinator_v1.py"
    sasang_response_script = root / "scripts" / "build_sasang_rule_based_response_v1.py"
    status_board_script = root / "scripts" / "build_agct_sasang_global_status_board_v1.py"

    repro_out = root / "reports" / "agct_sigma_fixed_repro_3batch_v1_latest.json"
    daily_out = root / "reports" / "agct_daily_formula_drift_chain_v1_latest.json"
    h2h_out = root / "reports" / "agct_sigma_head_to_head_3batch_v1_latest.json"
    sasang_reasoning_out = root / "reports" / "sasang_dna_market_reasoning_v1_latest.json"
    coordinator_out = root / "reports" / "mkm_global_coordinator_v1_latest.json"
    sasang_response_out = root / "reports" / "sasang_rule_based_response_v1_latest.json"
    sasang_response_md_out = root / "reports" / "sasang_rule_based_response_v1_latest.md"
    status_board_out = root / "reports" / "agct_sasang_global_status_board_v1_latest.json"
    status_board_md_out = root / "reports" / "agct_sasang_global_status_board_v1_latest.md"

    print("[STEP] repro", flush=True)
    _run(
        [
            sys.executable,
            str(repro_script),
            "--sigma",
            str(locked_sigma),
            "--trials",
            str(ns.repro_trials),
            "--base-seed",
            str(ns.base_seed),
            "--batch-gap",
            str(ns.batch_gap),
            "--n-batches",
            str(ns.repro_batches),
            "--output-json",
            str(repro_out),
        ],
        root,
    )

    _run(
        [
            sys.executable,
            str(sasang_reasoning_script),
            "--market-psych-csv",
            str(ns.market_psych_csv),
            "--dna-weight",
            str(ns.sasang_dna_weight),
            "--market-weight",
            str(ns.sasang_market_weight),
            "--output-json",
            str(sasang_reasoning_out),
        ],
        root,
    )

    print("[STEP] daily_drift", flush=True)
    _run(
        [
            sys.executable,
            str(daily_script),
            "--seed",
            str(ns.daily_seed),
            "--drift-runs",
            str(ns.daily_drift_runs),
            "--drift-start-seed",
            str(ns.base_seed),
            "--output-json",
            str(daily_out),
        ],
        root,
    )

    print("[STEP] h2h", flush=True)
    _run(
        [
            sys.executable,
            str(h2h_script),
            "--sigmas",
            ns.h2h_sigmas,
            "--trials",
            str(ns.h2h_trials),
            "--base-seed",
            str(ns.base_seed),
            "--batch-gap",
            str(ns.batch_gap),
            "--n-batches",
            str(ns.h2h_batches),
            "--output-json",
            str(h2h_out),
        ],
        root,
    )

    print("[STEP] global_coordinator", flush=True)
    _run(
        [
            sys.executable,
            str(coordinator_script),
            "--sasang-json",
            str(sasang_reasoning_out),
            "--output-json",
            str(coordinator_out),
        ],
        root,
    )

    repro = _read_json(repro_out)
    daily = _read_json(daily_out)
    h2h = _read_json(h2h_out)
    sasang_reasoning = _read_json(sasang_reasoning_out)
    coordinator = _read_json(coordinator_out)
    repro_summary = repro.get("summary", {})
    daily_summary = daily.get("daily", {})
    h2h_winner_sigma = h2h.get("winner", {}).get("sigma")
    h2h_rows = h2h.get("rows") if isinstance(h2h.get("rows"), list) else []
    tied_with_locked = False
    if h2h_rows:
        locked_row = next((r for r in h2h_rows if float(r.get("sigma", -999)) == float(locked_sigma)), None)
        winner_row = next(
            (r for r in h2h_rows if float(r.get("sigma", -999)) == float(h2h_winner_sigma))
            if h2h_winner_sigma is not None
            else None,
            None,
        )
        if isinstance(locked_row, dict) and isinstance(winner_row, dict):
            lg = float(locked_row.get("go_rate_mean", 0.0))
            lt = float(locked_row.get("transition_intensity_mean", 0.0))
            wg = float(winner_row.get("go_rate_mean", 0.0))
            wt = float(winner_row.get("transition_intensity_mean", 0.0))
            tied_with_locked = abs(lg - wg) <= TIE_EPS and abs(lt - wt) <= TIE_EPS

    repro_go_rate_mean = float(repro_summary.get("go_rate_mean") or 0.0)
    transition_intensity_mean = float(repro_summary.get("transition_intensity_mean") or 0.0)
    daily_after = daily_summary.get("decision_after")

    hard_enforcement = int(ns.repro_trials) >= int(ns.min_trials_for_hard_enforcement)
    repro_go_ok = repro_go_rate_mean >= ns.alert_go_rate_min
    repro_ti_ok = transition_intensity_mean >= ns.alert_transition_intensity_min
    checks = {
        "repro_go_rate_min_ok": repro_go_ok,
        "repro_transition_intensity_min_ok": repro_ti_ok,
        "daily_after_go_ok": daily_after == "GO_BTRACK",
        "h2h_locked_sigma_wins_ok": (h2h_winner_sigma == locked_sigma) or tied_with_locked,
        "sasang_lane_news_excluded_ok": bool(sasang_reasoning.get("governance", {}).get("news_history_lane_excluded", False)),
    }
    alert_reasons = []
    soft_reasons = []
    if not checks["repro_go_rate_min_ok"]:
        (alert_reasons if hard_enforcement else soft_reasons).append("repro_go_rate_below_min")
    if not checks["repro_transition_intensity_min_ok"]:
        (alert_reasons if hard_enforcement else soft_reasons).append("repro_transition_intensity_below_min")
    if not checks["daily_after_go_ok"]:
        alert_reasons.append("daily_after_not_go")
    if not checks["h2h_locked_sigma_wins_ok"]:
        alert_reasons.append("h2h_winner_changed")
    if not checks["sasang_lane_news_excluded_ok"]:
        alert_reasons.append("sasang_lane_news_exclusion_failed")
    status = "PASS"
    if alert_reasons:
        status = "ALERT"
    elif soft_reasons:
        status = "WARN"

    payload = {
        "schema": "agct_sigma_locked_baseline_chain_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "locked_sigma": locked_sigma,
        "inputs": {
            "sigma_policy_json": str(ns.sigma_policy_json.resolve()) if ns.sigma_policy_json else None,
            "base_seed": ns.base_seed,
            "batch_gap": ns.batch_gap,
            "repro_trials": ns.repro_trials,
            "repro_batches": ns.repro_batches,
            "daily_seed": ns.daily_seed,
            "daily_drift_runs": ns.daily_drift_runs,
            "h2h_sigmas": ns.h2h_sigmas,
            "h2h_trials": ns.h2h_trials,
            "h2h_batches": ns.h2h_batches,
            "market_psych_csv": str(ns.market_psych_csv.resolve()) if ns.market_psych_csv.is_file() else str(ns.market_psych_csv),
            "sasang_dna_weight": ns.sasang_dna_weight,
            "sasang_market_weight": ns.sasang_market_weight,
            "alert_go_rate_min": ns.alert_go_rate_min,
            "alert_transition_intensity_min": ns.alert_transition_intensity_min,
        },
        "summary": {
            "status": status,
            "repro_go_rate_mean": repro_summary.get("go_rate_mean"),
            "repro_go_rate_std": repro_summary.get("go_rate_std"),
            "repro_transition_intensity_mean": repro_summary.get("transition_intensity_mean"),
            "repro_transition_intensity_std": repro_summary.get("transition_intensity_std"),
            "daily_decision_before": daily_summary.get("decision_before"),
            "daily_decision_after": daily_after,
            "h2h_winner_sigma": h2h_winner_sigma,
            "h2h_tied_with_locked_sigma": tied_with_locked,
            "hard_enforcement_applied": hard_enforcement,
            "soft_reasons": soft_reasons,
            "sasang_latest_top_axis": sasang_reasoning.get("summary", {}).get("latest_top_axis"),
            "sasang_alignment_corr": sasang_reasoning.get("summary", {}).get("alignment_corr_ty_sy_vs_te_se"),
            "sasang_byung_state": sasang_reasoning.get("byungjeungyakri_transition", {}).get("state"),
            "global_coordinator_action": coordinator.get("decision", {}).get("action"),
            "checks": checks,
            "alert_reasons": alert_reasons,
        },
        "artifacts": {
            "repro_report": str(repro_out.resolve()),
            "daily_report": str(daily_out.resolve()),
            "h2h_report": str(h2h_out.resolve()),
            "sasang_reasoning_report": str(sasang_reasoning_out.resolve()),
            "global_coordinator_report": str(coordinator_out.resolve()),
            "sasang_rule_response_json": str(sasang_response_out.resolve()),
            "sasang_rule_response_md": str(sasang_response_md_out.resolve()),
            "unified_status_board_json": str(status_board_out.resolve()),
            "unified_status_board_md": str(status_board_md_out.resolve()),
        },
        "notes": [
            "Locked baseline chain is B-track only.",
            "No A-track/live trading authority is implied.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[STEP] sasang_rule_response", flush=True)
    _run(
        [
            sys.executable,
            str(sasang_response_script),
            "--reasoning-json",
            str(sasang_reasoning_out),
            "--baseline-json",
            str(ns.output_json),
            "--output-json",
            str(sasang_response_out),
            "--output-md",
            str(sasang_response_md_out),
        ],
        root,
    )
    print("[STEP] unified_status_board", flush=True)
    _run(
        [
            sys.executable,
            str(status_board_script),
            "--baseline-json",
            str(ns.output_json),
            "--h2h-json",
            str(h2h_out),
            "--reasoning-json",
            str(sasang_reasoning_out),
            "--coordinator-json",
            str(coordinator_out),
            "--output-json",
            str(status_board_out),
            "--output-md",
            str(status_board_md_out),
        ],
        root,
    )
    if ns.run_regression_check:
        regression_script = root / "scripts" / "check_agct_locked_baseline_regression_v1.py"
        print("[STEP] regression_check", flush=True)
        cmd = [
            sys.executable,
            str(regression_script),
            "--latest-json",
            str(ns.output_json),
            "--baseline-json",
            str(ns.regression_baseline_json),
            "--min-go-rate",
            str(ns.alert_go_rate_min),
            "--min-transition-intensity",
            str(ns.alert_transition_intensity_min),
        ]
        t0 = time.perf_counter()
        print(f"[RUN] {' '.join(cmd)}", flush=True)
        r = subprocess.run(cmd, cwd=str(root), capture_output=False, text=True, check=False)
        dt = time.perf_counter() - t0
        if r.returncode != 0:
            if ns.strict_regression_check:
                raise RuntimeError(f"regression_check_failed returncode={r.returncode} elapsed_sec={dt:.1f}")
            print(
                f"[WARN] regression_check returncode={r.returncode} elapsed_sec={dt:.1f} (soft-fail mode)",
                flush=True,
            )
        else:
            print(f"[DONE] elapsed_sec={dt:.1f}", flush=True)
    print(f"WROTE: {ns.output_json.resolve()} locked_sigma={locked_sigma}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
