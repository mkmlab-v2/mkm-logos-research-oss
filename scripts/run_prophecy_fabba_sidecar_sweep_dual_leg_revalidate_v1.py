#!/usr/bin/env python3
"""[HYPO] Re-validate sweep-best tol/ngram on dual-leg 180d/2bps (overfit check)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_fabba_sidecar_lib_v1 import (  # noqa: E402
    load_dual_leg_intersection_window,
    pool_arms_across_instruments,
    run_blocked_wf_arms_for_panel,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_SWEEP = ROOT / "reports/prophecy_fabba_sidecar_param_sweep_v1_latest.json"
DEFAULT_BASELINE = ROOT / "reports/prophecy_fabba_sidecar_dual_leg_wf_v1_latest.json"
DEFAULT_PRIMARY = ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1_latest.json"
SCHEMA = "prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1"

DEFAULT_TOL = 0.05
DEFAULT_NGRAM = 3
DEFAULT_LOOKBACK = 20


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _arm_pooled(arms: list[dict[str, Any]], arm_id: str) -> dict[str, Any]:
    for a in arms:
        if a.get("arm_id") == arm_id:
            return a
    return {}


def _run_dual_leg_variant(
    *,
    kospi_csv: Path,
    btc_csv: Path,
    last_n: int,
    n_folds: int,
    neutral_bps: float,
    lookback: int,
    ngram_size: int,
    tol: float,
    backend: str,
) -> list[dict[str, Any]]:
    window = load_dual_leg_intersection_window(kospi_csv, btc_csv, last_n_intersection=last_n)
    if window.get("status") != "ok":
        raise RuntimeError(f"intersection window failed: {window}")
    eval_dates = window["intersection_dates"]
    per_inst = []
    for inst_id in ("kospi", "btc"):
        panel = window["panels"][inst_id]
        per_inst.append(
            run_blocked_wf_arms_for_panel(
                instrument_id=inst_id,
                dates=panel["dates"],
                closes=panel["closes"],
                eval_dates=eval_dates,
                n_folds=n_folds,
                neutral_bps=neutral_bps,
                lookback=lookback,
                ngram_size=ngram_size,
                tol=tol,
                backend=backend,
                alpha=0.1,
            )
        )
    return pool_arms_across_instruments(per_inst)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--last-n-intersection", type=int, default=180)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK)
    ap.add_argument("--backend", default="apca_stub")
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--baseline-dual-leg-json", type=Path, default=DEFAULT_BASELINE)
    ap.add_argument("--primary-hit-json", type=Path, default=DEFAULT_PRIMARY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--overfit-drop-pp", type=float, default=10.0, help="Flag if sweep kospi-only HR minus dual-leg HR exceeds this")
    args = ap.parse_args(argv)

    sweep_doc = _load(args.sweep_json) or {}
    best = sweep_doc.get("best_by_ngram_pooled_hr") or {}
    sweep_tol = float(best.get("tol", 0.03))
    sweep_ngram = int(best.get("ngram_size", 2))
    sweep_kospi_hr = best.get("ngram_pooled_hr")

    default_pooled = _run_dual_leg_variant(
        kospi_csv=args.kospi_csv,
        btc_csv=args.btc_csv,
        last_n=args.last_n_intersection,
        n_folds=args.n_folds,
        neutral_bps=args.neutral_bps,
        lookback=args.lookback,
        ngram_size=DEFAULT_NGRAM,
        tol=DEFAULT_TOL,
        backend=args.backend,
    )
    sweep_pooled = _run_dual_leg_variant(
        kospi_csv=args.kospi_csv,
        btc_csv=args.btc_csv,
        last_n=args.last_n_intersection,
        n_folds=args.n_folds,
        neutral_bps=args.neutral_bps,
        lookback=args.lookback,
        ngram_size=sweep_ngram,
        tol=sweep_tol,
        backend=args.backend,
    )

    def _ngram(arms: list[dict[str, Any]]) -> dict[str, Any]:
        return _arm_pooled(arms, "fabba_sidecar_ngram_lut")

    def_n = _ngram(default_pooled)
    swp_n = _ngram(sweep_pooled)
    def_hr = def_n.get("pooled_test_directional_hit_rate")
    swp_hr = swp_n.get("pooled_test_directional_hit_rate")

    primary = _load(args.primary_hit_json) or {}
    primary_hr = (primary.get("metrics") or {}).get("price_directional_hit_rate")

    kospi_only_minus_dual_pp = None
    if sweep_kospi_hr is not None and swp_hr is not None:
        kospi_only_minus_dual_pp = round(float(sweep_kospi_hr) - float(swp_hr), 6)

    overfit_flag = (
        kospi_only_minus_dual_pp is not None and kospi_only_minus_dual_pp >= args.overfit_drop_pp
    )

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_mutated": False,
        "protocol": {
            "last_n_intersection": args.last_n_intersection,
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
            "lookback": args.lookback,
            "backend": args.backend,
        },
        "sweep_best_source": str(args.sweep_json.relative_to(ROOT)).replace("\\", "/"),
        "sweep_best_kospi_only": best,
        "variants": {
            "default_dual_leg": {
                "tol": DEFAULT_TOL,
                "ngram_size": DEFAULT_NGRAM,
                "dual_leg_pooled_arms": default_pooled,
                "ngram_summary": {
                    "pooled_hr": def_hr,
                    "total_n_evaluated": def_n.get("total_n_evaluated"),
                    "total_price_hits": def_n.get("total_price_hits"),
                },
            },
            "sweep_best_dual_leg": {
                "tol": sweep_tol,
                "ngram_size": sweep_ngram,
                "dual_leg_pooled_arms": sweep_pooled,
                "ngram_summary": {
                    "pooled_hr": swp_hr,
                    "total_n_evaluated": swp_n.get("total_n_evaluated"),
                    "total_price_hits": swp_n.get("total_price_hits"),
                },
            },
        },
        "delta": {
            "sweep_best_vs_default_dual_leg_pp": round(float(swp_hr) - float(def_hr), 6)
            if swp_hr is not None and def_hr is not None
            else None,
            "sweep_best_vs_primary_pp": round(float(swp_hr) - float(primary_hr), 6)
            if swp_hr is not None and primary_hr is not None
            else None,
            "kospi_only_sweep_vs_dual_leg_sweep_pp": kospi_only_minus_dual_pp,
        },
        "overfit_assessment": {
            "kospi_only_to_dual_leg_drop_pp": kospi_only_minus_dual_pp,
            "threshold_pp": args.overfit_drop_pp,
            "likely_overfit_to_kospi_intersection": overfit_flag,
            "recommended_shadow_params": {
                "tol": sweep_tol if not overfit_flag else DEFAULT_TOL,
                "ngram_size": sweep_ngram if not overfit_flag else DEFAULT_NGRAM,
                "reason": "dual-leg confirms sweep best"
                if not overfit_flag
                else "revert to default — sweep best collapses on dual-leg",
            },
        },
        "compare_primary": {
            "primary_hr": primary_hr,
            "primary_n": (primary.get("metrics") or {}).get("n_evaluated"),
        },
        "reproduce": (
            f"py scripts/run_prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1.py "
            f"--sweep-json {args.sweep_json}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} "
        f"default={def_hr} sweep_dual={swp_hr} overfit={overfit_flag}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
