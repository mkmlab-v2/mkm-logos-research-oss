#!/usr/bin/env python3
"""Run Logos directional revalidation suite and emit summary artifact.

Research-only orchestrator:
1) lens combo backtest (with/without logos)
2) role-router multiscenario optimization
3) strict OOS gate
4) consolidated summary for operator review
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
LOGOS_REVAL_TMP_ROOT = ROOT / "tmp" / "logos_reval"

DEFAULT_SCORE_JSON = ART / "btrack_prophecy_score_30y_dual_latest.json"
DEFAULT_SIDECAR_JSON = ART / "btrack_prophecy_score_insight_sidecar_30y_latest.json"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"

DEFAULT_LENS_OUT = ART / "prophecy_logos_revalidation_lens_combo_latest.json"
DEFAULT_ROUTER_OUT = ART / "prophecy_logos_revalidation_role_router_opt_latest.json"
DEFAULT_OOS_OUT = ART / "prophecy_logos_revalidation_oos_gate_latest.json"
DEFAULT_SUMMARY_OUT = ART / "prophecy_logos_revalidation_summary_latest.json"
DEFAULT_PROMOTION_GATE = ART / "role_router_shadow_forward_validation_gate_v1.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _panel_row_count(score_json: Path, target_instrument: str) -> int:
    doc = _read_json(score_json)
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    inst = target_instrument.strip().lower()
    return sum(
        1
        for r in rows
        if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == inst
    )


def _safe_float(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": int(proc.returncode),
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _write_temp_score_variant(score_json: Path, target_instrument: str, allowed_dirs: set[str]) -> Path:
    src = _read_json(score_json)
    rows = src.get("rows") if isinstance(src.get("rows"), list) else []
    filt: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        inst = str(r.get("instrument") or "").strip().lower()
        d = str(r.get("actual_direction") or "").strip().lower()
        if inst == target_instrument.lower() and d in allowed_dirs:
            filt.append(r)
    out_doc = dict(src)
    out_doc["rows"] = filt
    LOGOS_REVAL_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="run_", dir=str(LOGOS_REVAL_TMP_ROOT)))
    tmp = tmp_dir / f"score_{target_instrument}_{'_'.join(sorted(allowed_dirs))}.json"
    tmp.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return tmp


def _find_best_logos_vs_nonlogos(lens_doc: dict[str, Any]) -> dict[str, Any]:
    ranked = lens_doc.get("ranked_strategies") if isinstance(lens_doc.get("ranked_strategies"), list) else []
    best_logos = None
    best_nonlogos = None
    for item in ranked:
        if not isinstance(item, dict):
            continue
        lenses = item.get("lenses") if isinstance(item.get("lenses"), list) else []
        has_logos = any(str(x).strip().lower() == "logos" for x in lenses)
        if has_logos and best_logos is None:
            best_logos = item
        if (not has_logos) and best_nonlogos is None:
            best_nonlogos = item
        if best_logos is not None and best_nonlogos is not None:
            break

    def _extract(x: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(x, dict):
            return {}
        m = x.get("metrics") if isinstance(x.get("metrics"), dict) else {}
        return {
            "strategy_id": x.get("strategy_id"),
            "lenses": x.get("lenses"),
            "use_coordinator": bool(x.get("use_coordinator")),
            "metrics": {
                "total_return": _safe_float(m.get("total_return")),
                "cagr": _safe_float(m.get("cagr")),
                "mdd": _safe_float(m.get("mdd")),
                "sharpe": _safe_float(m.get("sharpe")),
                "directional_hit_rate_active": _safe_float(m.get("directional_hit_rate_active")),
            },
        }

    logos_e = _extract(best_logos)
    nonlogos_e = _extract(best_nonlogos)
    logos_m = logos_e.get("metrics") if isinstance(logos_e.get("metrics"), dict) else {}
    nonlogos_m = nonlogos_e.get("metrics") if isinstance(nonlogos_e.get("metrics"), dict) else {}
    return {
        "best_logos_including": logos_e,
        "best_non_logos": nonlogos_e,
        "delta_nonlogos_minus_logos": {
            "total_return": _safe_float(nonlogos_m.get("total_return")) - _safe_float(logos_m.get("total_return")),
            "cagr": _safe_float(nonlogos_m.get("cagr")) - _safe_float(logos_m.get("cagr")),
            "mdd": _safe_float(nonlogos_m.get("mdd")) - _safe_float(logos_m.get("mdd")),
            "sharpe": _safe_float(nonlogos_m.get("sharpe")) - _safe_float(logos_m.get("sharpe")),
            "hit_rate_active": _safe_float(nonlogos_m.get("directional_hit_rate_active"))
            - _safe_float(logos_m.get("directional_hit_rate_active")),
        },
    }


def _best_nonlogos_strategy(lens_doc: dict[str, Any]) -> dict[str, Any]:
    ranked = lens_doc.get("ranked_strategies") if isinstance(lens_doc.get("ranked_strategies"), list) else []
    for item in ranked:
        if not isinstance(item, dict):
            continue
        lenses = item.get("lenses") if isinstance(item.get("lenses"), list) else []
        has_logos = any(str(x).strip().lower() == "logos" for x in lenses)
        if not has_logos:
            m = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
            return {
                "strategy_id": item.get("strategy_id"),
                "lenses": lenses,
                "metrics": {
                    "total_return": _safe_float(m.get("total_return")),
                    "cagr": _safe_float(m.get("cagr")),
                    "mdd": _safe_float(m.get("mdd")),
                    "sharpe": _safe_float(m.get("sharpe")),
                    "directional_hit_rate_active": _safe_float(m.get("directional_hit_rate_active")),
                },
            }
    return {}


def _compute_directional_viability_from_lens_output(lens_output_path: Path) -> bool | None:
    lens_doc = _read_json(lens_output_path)
    if not lens_doc:
        return None
    compare = _find_best_logos_vs_nonlogos(lens_doc)
    logos_metrics = ((compare.get("best_logos_including") or {}).get("metrics")) or {}
    if not logos_metrics:
        return None
    return (
        _safe_float(logos_metrics.get("sharpe")) > 0.0
        and _safe_float(logos_metrics.get("total_return")) > 0.0
        and _safe_float(logos_metrics.get("mdd")) >= -0.25
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE_JSON)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR_JSON)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--target-instrument", type=str, default="kospi")
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--annual-trading-days", type=int, default=252)
    ap.add_argument("--lens-output", type=Path, default=DEFAULT_LENS_OUT)
    ap.add_argument("--router-output", type=Path, default=DEFAULT_ROUTER_OUT)
    ap.add_argument("--oos-output", type=Path, default=DEFAULT_OOS_OUT)
    ap.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUT)
    ap.add_argument("--promotion-gate-json", type=Path, default=DEFAULT_PROMOTION_GATE)
    ap.add_argument(
        "--strict-shadow-forward-mode",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When enabled, align optimizer/OOS windows with 31.71 hard-lock intent (required_oos_days=252).",
    )
    ap.add_argument(
        "--quick-mode",
        action="store_true",
        default=True,
        help="Use reduced grids for faster operator feedback (default: on).",
    )
    args = ap.parse_args()

    if args.strict_shadow_forward_mode:
        router_oos_grid = "252"
        router_lookback_grid = "63"
        router_neutral_grid = "0.5"
        router_conflict_grid = "0.1,0.2"
        router_dz_grid = "0.005"
        oos_tail_days = "252"
    elif args.quick_mode:
        router_oos_grid = "60"
        router_lookback_grid = "21"
        router_neutral_grid = "0.7"
        router_conflict_grid = "0.1,0.2"
        router_dz_grid = "0.005"
        oos_tail_days = "120"
    else:
        router_oos_grid = "60,120,252"
        router_lookback_grid = "21,63,126"
        router_neutral_grid = "0.3,0.5,0.7"
        router_conflict_grid = "0.1,0.2,0.3"
        router_dz_grid = "0.003,0.005,0.01,0.02"
        oos_tail_days = "252"

  # Short panels (e.g. 30d dual-leg): strict/ quick defaults (120–252) exceed row count.
    panel_n = _panel_row_count(args.score_json, args.target_instrument)
    if panel_n > 0:
        max_tail = max(3, panel_n - 10)
        try:
            requested_tail = int(oos_tail_days)
        except ValueError:
            requested_tail = max_tail
        if requested_tail >= panel_n:
            oos_tail_days = str(max_tail)

    lens_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_prophecy_lens_combo_backtest_v1.py"),
        "--score-json",
        str(args.score_json),
        "--sidecar-json",
        str(args.sidecar_json),
        "--btc-csv",
        str(args.btc_csv),
        "--target-instrument",
        str(args.target_instrument),
        "--fee-bps",
        str(args.fee_bps),
        "--annual-trading-days",
        str(args.annual_trading_days),
        "--walkforward-mode",
        "expanding",
        "--walkforward-test-window-rows",
        "10",
        "--walkforward-min-train-rows",
        "30",
        "--output",
        str(args.lens_output),
        "--logos-vote-mode",
        "global",
    ]
    router_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_prophecy_role_router_multiscenario_opt_v1.py"),
        "--score-json",
        str(args.score_json),
        "--sidecar-json",
        str(args.sidecar_json),
        "--btc-csv",
        str(args.btc_csv),
        "--target-instrument",
        str(args.target_instrument),
        "--fee-bps",
        str(args.fee_bps),
        "--annual-trading-days",
        str(args.annual_trading_days),
        "--oos-days-grid",
        router_oos_grid,
        "--month-lookback-grid",
        router_lookback_grid,
        "--neutral-size-grid",
        router_neutral_grid,
        "--strength-aligned-grid",
        "1.0",
        "--strength-neutral-grid",
        "0.5,0.6",
        "--strength-conflict-grid",
        router_conflict_grid,
        "--coord-policies",
        "off,confirm_only,regime_transition_only",
        "--coord-deadzone-grid",
        router_dz_grid,
        "--neutral-base-sources",
        "off,coord",
        "--top-k",
        "20",
        "--promotion-gate-json",
        str(args.promotion_gate_json),
        "--output",
        str(args.router_output),
    ]
    oos_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_prophecy_lens_role_router_oos_gate_v1.py"),
        "--score-json",
        str(args.score_json),
        "--sidecar-json",
        str(args.sidecar_json),
        "--btc-csv",
        str(args.btc_csv),
        "--target-instrument",
        str(args.target_instrument),
        "--fee-bps",
        str(args.fee_bps),
        "--annual-trading-days",
        str(args.annual_trading_days),
        "--oos-tail-days",
        oos_tail_days,
        "--month-lookback-grid",
        "21,63,126",
        "--neutral-size-grid",
        "0.3,0.5,0.7",
        "--gate-min-hit-rate",
        "0.52",
        "--gate-max-mdd",
        "-0.25",
        "--gate-min-sharpe",
        "0.0",
        "--gate-min-total-return",
        "0.0",
        "--output",
        str(args.oos_output),
    ]

    # Additional evaluation: bull-only / bear-only regime split (same harness).
    bull_score_json = _write_temp_score_variant(args.score_json, args.target_instrument, {"bull"})
    bear_score_json = _write_temp_score_variant(args.score_json, args.target_instrument, {"bear"})
    bull_lens_out = args.lens_output.with_name(args.lens_output.name.replace("_latest.json", "_bull_only_latest.json"))
    bear_lens_out = args.lens_output.with_name(args.lens_output.name.replace("_latest.json", "_bear_only_latest.json"))
    bull_lens_cmd = lens_cmd.copy()
    bear_lens_cmd = lens_cmd.copy()
    bull_lens_cmd[bull_lens_cmd.index("--score-json") + 1] = str(bull_score_json)
    bull_lens_cmd[bull_lens_cmd.index("--output") + 1] = str(bull_lens_out)
    bear_lens_cmd[bear_lens_cmd.index("--score-json") + 1] = str(bear_score_json)
    bear_lens_cmd[bear_lens_cmd.index("--output") + 1] = str(bear_lens_out)
    # Prevent bull/bear sub-runs from overwriting the main limited-live top1 candidate.
    bull_candidate_out = args.lens_output.with_name(
        args.lens_output.name.replace("_latest.json", "_bull_only_top1_candidate_latest.json")
    )
    bear_candidate_out = args.lens_output.with_name(
        args.lens_output.name.replace("_latest.json", "_bear_only_top1_candidate_latest.json")
    )
    bull_lens_cmd.extend(["--emit-top1-candidate", str(bull_candidate_out)])
    bear_lens_cmd.extend(["--emit-top1-candidate", str(bear_candidate_out)])

    runs = {
        "lens_combo_backtest": _run(lens_cmd),
        "role_router_multiscenario_opt": _run(router_cmd),
        "strict_oos_gate": _run(oos_cmd),
        "bull_only_lens_combo_backtest": _run(bull_lens_cmd),
        "bear_only_lens_combo_backtest": _run(bear_lens_cmd),
    }

    for k in (
        "lens_combo_backtest",
        "role_router_multiscenario_opt",
        "strict_oos_gate",
        "bull_only_lens_combo_backtest",
        "bear_only_lens_combo_backtest",
    ):
        if runs[k]["returncode"] != 0:
            directional_viable_partial = _compute_directional_viability_from_lens_output(args.lens_output)
            router_doc_partial = _read_json(args.router_output)
            decision_doc_partial = _read_json(ROOT / "reports" / "role_router_shadow_forward_validation_decision_latest.json")
            out = {
                "schema": "prophecy_logos_revalidation_summary_v1",
                "generated_at_utc": _now(),
                "status": "FAILED",
                "failed_step": k,
                "runs": runs,
                "findings": {
                    "router_selection_policy": router_doc_partial.get("selection_policy"),
                    "shadow_forward_validation_decision": {
                        "final_decision": decision_doc_partial.get("final_decision"),
                        "checks_passed": decision_doc_partial.get("checks_passed"),
                        "thresholds_passed": decision_doc_partial.get("thresholds_passed"),
                        "failed_reasons": decision_doc_partial.get("failed_reasons"),
                    },
                    "logos_directional_viable_under_current_setup": directional_viable_partial,
                },
            }
            args.summary_output.parent.mkdir(parents=True, exist_ok=True)
            args.summary_output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"WROTE: {args.summary_output}")
            print(f"FAILED_STEP: {k}")
            return 1

    lens_doc = _read_json(args.lens_output)
    router_doc = _read_json(args.router_output)
    oos_doc = _read_json(args.oos_output)
    bull_lens_doc = _read_json(bull_lens_out)
    bear_lens_doc = _read_json(bear_lens_out)

    compare = _find_best_logos_vs_nonlogos(lens_doc)
    bull_best_nonlogos = _best_nonlogos_strategy(bull_lens_doc)
    bear_best_nonlogos = _best_nonlogos_strategy(bear_lens_doc)
    best_router = router_doc.get("best_candidate") if isinstance(router_doc.get("best_candidate"), dict) else {}
    oos_gate = oos_doc.get("gate") if isinstance(oos_doc.get("gate"), dict) else {}

    # OOS-window sensitivity (proxy for label/window robustness under current score panel).
    oos_windows = [60, 120, 252]
    window_sensitivity: list[dict[str, Any]] = []
    for w in oos_windows:
        out_w = args.oos_output.with_name(args.oos_output.name.replace("_latest.json", f"_{w}d_latest.json"))
        cmd_w = oos_cmd.copy()
        cmd_w[cmd_w.index("--oos-tail-days") + 1] = str(w)
        cmd_w[cmd_w.index("--output") + 1] = str(out_w)
        res_w = _run(cmd_w)
        out_doc = _read_json(out_w)
        gate_w = out_doc.get("gate") if isinstance(out_doc.get("gate"), dict) else {}
        window_sensitivity.append(
            {
                "oos_tail_days": w,
                "run_returncode": int(res_w.get("returncode", 1)),
                "gate_status": gate_w.get("status"),
                "go": bool(gate_w.get("go", False)),
                "checks": gate_w.get("checks"),
                "output": str(out_w),
            }
        )

    # 31.71 fusion: evaluate final shadow-forward promotion decision.
    decision_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_role_router_shadow_forward_validation_v1.py"),
        "--gate-json",
        str(args.promotion_gate_json),
    ]
    runs["shadow_forward_validation_decision"] = _run(decision_cmd)
    decision_doc = _read_json(ROOT / "reports" / "role_router_shadow_forward_validation_decision_latest.json")

    logos_metrics = ((compare.get("best_logos_including") or {}).get("metrics")) or {}
    directional_viable = (
        _safe_float(logos_metrics.get("sharpe")) > 0.0
        and _safe_float(logos_metrics.get("total_return")) > 0.0
        and _safe_float(logos_metrics.get("mdd")) >= -0.25
    )

    summary = {
        "schema": "prophecy_logos_revalidation_summary_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "status": "OK",
        "inputs": {
            "score_json": str(args.score_json),
            "sidecar_json": str(args.sidecar_json),
            "btc_csv": str(args.btc_csv),
            "target_instrument": str(args.target_instrument),
            "fee_bps": float(args.fee_bps),
            "promotion_gate_json": str(args.promotion_gate_json),
        },
        "outputs": {
            "lens_output": str(args.lens_output),
            "router_output": str(args.router_output),
            "oos_output": str(args.oos_output),
            "bull_lens_output": str(bull_lens_out),
            "bear_lens_output": str(bear_lens_out),
        },
        "runs": runs,
        "findings": {
            "logos_vs_nonlogos": compare,
            "bull_only_best_nonlogos": bull_best_nonlogos,
            "bear_only_best_nonlogos": bear_best_nonlogos,
            "best_router_candidate": best_router,
            "router_selection_policy": router_doc.get("selection_policy"),
            "strict_oos_gate": oos_gate,
            "oos_window_sensitivity": window_sensitivity,
            "shadow_forward_validation_decision": {
                "final_decision": decision_doc.get("final_decision"),
                "checks_passed": decision_doc.get("checks_passed"),
                "thresholds_passed": decision_doc.get("thresholds_passed"),
                "failed_reasons": decision_doc.get("failed_reasons"),
            },
            "logos_directional_viable_under_current_setup": directional_viable,
        },
        "next_checks": [
            "Inspect edge-path attribution for triggered logos warnings.",
            "Re-run with alternate label windows for directional target.",
            "Stress-test with separate bull/bear subperiod slices.",
        ],
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.summary_output}")
    print(f"logos_directional_viable_under_current_setup={directional_viable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

