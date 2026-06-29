#!/usr/bin/env python3
"""[HYPO] Dual-leg intersection fABBA sidecar WF (180d / 2bps parity with recommended chain).

Blocked walk-forward on KOSPI+BTC calendar intersection; pools hits across legs
(n_evaluated ~ 360 style). B-track only — no Primary score mutation.
"""

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
    fabba_dependency_probe,
    load_dual_leg_intersection_window,
    pool_arms_across_instruments,
    run_blocked_wf_arms_for_panel,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_sidecar_dual_leg_wf_v1_latest.json"
DEFAULT_PRIMARY_HIT = ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json"
SCHEMA = "prophecy_fabba_sidecar_dual_leg_wf_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--last-n-intersection", type=int, default=180)
    ap.add_argument("--n-folds", type=int, default=6, help="Match recommended eval chain default")
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--ngram-size", type=int, default=3)
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--backend", choices=("auto", "apca_stub", "fabba"), default="auto")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--primary-hit-json", type=Path, default=DEFAULT_PRIMARY_HIT)
    args = ap.parse_args(argv)

    window = load_dual_leg_intersection_window(
        args.kospi_csv,
        args.btc_csv,
        last_n_intersection=args.last_n_intersection,
    )
    if window.get("status") != "ok":
        print(f"dual-leg window failed: {window}", file=sys.stderr)
        return 2

    eval_dates = window["intersection_dates"]
    per_inst: list[dict[str, Any]] = []
    for inst_id in ("kospi", "btc"):
        panel = window["panels"][inst_id]
        per_inst.append(
            run_blocked_wf_arms_for_panel(
                instrument_id=inst_id,
                dates=panel["dates"],
                closes=panel["closes"],
                eval_dates=eval_dates,
                n_folds=args.n_folds,
                neutral_bps=args.neutral_bps,
                lookback=args.lookback,
                ngram_size=args.ngram_size,
                tol=args.tol,
                backend=args.backend,
                alpha=args.alpha,
            )
        )

    pooled = pool_arms_across_instruments(per_inst)
    primary = _load_json(args.primary_hit_json)
    primary_hr = (primary or {}).get("metrics", {}).get("price_directional_hit_rate")
    primary_n = (primary or {}).get("metrics", {}).get("n_evaluated")

    def _arm_hr(arm_id: str) -> float | None:
        for a in pooled:
            if a.get("arm_id") == arm_id:
                return a.get("pooled_test_directional_hit_rate")
        return None

    ngram_hr = _arm_hr("fabba_sidecar_ngram_lut")
    slope_hr = _arm_hr("fabba_sidecar_last_slope")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_mutated": False,
        "fabba_dependency_probe": fabba_dependency_probe(),
        "protocol": {
            "panel": "dual_leg_kospi_btc_intersection",
            "last_n_intersection": args.last_n_intersection,
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
            "lookback": args.lookback,
            "ngram_size": args.ngram_size,
            "tol": args.tol,
            "backend_requested": args.backend,
            "eval_date_from": window["eval_date_from"],
            "eval_date_to": window["eval_date_to"],
            "n_intersection_dates": window["n_intersection_dates"],
        },
        "per_instrument": per_inst,
        "dual_leg_pooled_arms": pooled,
        "compare_primary_recommended_chain": {
            "pointer": str(args.primary_hit_json.relative_to(ROOT)).replace("\\", "/")
            if primary
            else None,
            "primary_price_directional_hit_rate": primary_hr,
            "primary_n_evaluated": primary_n,
            "sidecar_ngram_pooled_hr": ngram_hr,
            "sidecar_ngram_vs_primary_pp": round(ngram_hr - primary_hr, 6)
            if ngram_hr is not None and primary_hr is not None
            else None,
            "sidecar_last_slope_pooled_hr": slope_hr,
            "sidecar_pooled_n_evaluated": next(
                (a.get("total_n_evaluated") for a in pooled if a.get("arm_id") == "fabba_sidecar_ngram_lut"),
                None,
            ),
            "note_ko": "Primary=ensemble score rows; sidecar=symbolic shadow only — KPI 합선 금지(FAIL-COMP-004)",
        },
        "reproduce": (
            f"py scripts/run_prophecy_fabba_sidecar_dual_leg_wf_v1.py "
            f"--last-n-intersection {args.last_n_intersection} --n-folds {args.n_folds} "
            f"--neutral-bps {args.neutral_bps}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} "
        f"ngram_pooled={ngram_hr} primary={primary_hr} "
        f"n_eval={out['compare_primary_recommended_chain'].get('sidecar_pooled_n_evaluated')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
