#!/usr/bin/env python3
"""[HYPO] fABBA wheel vs apca_stub A/B on dual-leg 180d/2bps shadow (B-track).

Runs blocked WF for both backends with sweep-best params (tol=0.03, ngram=2).
When fABBA Cython is unavailable (typical Windows), fabba arm falls back to
apca_stub and chain parity is recorded as skipped.

Linux repro included in artifact. No Track A merge.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_fabba_sidecar_lib_v1 import (  # noqa: E402
    compare_symbolic_backends_on_eval_points,
    fabba_dependency_probe,
    load_dual_leg_intersection_window,
    pool_arms_across_instruments,
    resolve_backend,
    run_blocked_wf_arms_for_panel,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_backend_ab_dual_leg_v1_latest.json"
DEFAULT_REVALIDATE = ROOT / "reports/prophecy_fabba_sidecar_sweep_dual_leg_revalidate_v1_latest.json"
DEFAULT_PRIMARY = ROOT / "reports/prophecy_hit_rate_eval_recommended_chain_run_latest.json"
SCHEMA = "prophecy_fabba_backend_ab_dual_leg_v1"


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


def _run_backend_panel(
    *,
    backend_requested: str,
    window: dict[str, Any],
    eval_dates: list[str],
    n_folds: int,
    neutral_bps: float,
    lookback: int,
    ngram_size: int,
    tol: float,
    alpha: float,
) -> dict[str, Any]:
    resolved, backend_meta = resolve_backend(backend_requested)
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
                backend=resolved,
                alpha=alpha,
            )
        )
    pooled = pool_arms_across_instruments(per_inst)
    chain_cmp: dict[str, Any] = {}
    for inst in per_inst:
        inst_id = inst.get("instrument_id")
        panel = window["panels"][inst_id]
        chain_cmp[inst_id] = compare_symbolic_backends_on_eval_points(
            dates=panel["dates"],
            closes=panel["closes"],
            eval_dates=eval_dates,
            lookback=lookback,
            tol=tol,
            alpha=alpha,
        )
    ngram = next((a for a in pooled if a.get("arm_id") == "fabba_sidecar_ngram_lut"), {})
    slope = next((a for a in pooled if a.get("arm_id") == "fabba_sidecar_last_slope"), {})
    return {
        "backend_requested": backend_requested,
        "backend_resolved": resolved,
        "backend_meta": backend_meta,
        "dual_leg_pooled_arms": pooled,
        "ngram_pooled_hr": ngram.get("pooled_test_directional_hit_rate"),
        "slope_pooled_hr": slope.get("pooled_test_directional_hit_rate"),
        "ngram_n_evaluated": ngram.get("total_n_evaluated"),
        "symbolic_chain_compare": chain_cmp,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--last-n-intersection", type=int, default=180)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--tol", type=float, default=0.03)
    ap.add_argument("--ngram-size", type=int, default=2)
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--revalidate-json", type=Path, default=DEFAULT_REVALIDATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    reval = _load(args.revalidate_json)
    if reval:
        best = (reval.get("sweep_best_kospi_only") or {})
        args.tol = float(best.get("tol") or args.tol)
        args.ngram_size = int(best.get("ngram_size") or args.ngram_size)

    window = load_dual_leg_intersection_window(
        args.kospi_csv,
        args.btc_csv,
        last_n_intersection=args.last_n_intersection,
    )
    if window.get("status") != "ok":
        print(f"dual-leg window failed: {window}", file=sys.stderr)
        return 2

    eval_dates = window["intersection_dates"]
    probe = fabba_dependency_probe()
    fabba_native = probe.get("status") == "dependency_ok"

    apca = _run_backend_panel(
        backend_requested="apca_stub",
        window=window,
        eval_dates=eval_dates,
        n_folds=args.n_folds,
        neutral_bps=args.neutral_bps,
        lookback=args.lookback,
        ngram_size=args.ngram_size,
        tol=args.tol,
        alpha=args.alpha,
    )
    fabba = _run_backend_panel(
        backend_requested="fabba",
        window=window,
        eval_dates=eval_dates,
        n_folds=args.n_folds,
        neutral_bps=args.neutral_bps,
        lookback=args.lookback,
        ngram_size=args.ngram_size,
        tol=args.tol,
        alpha=args.alpha,
    )

    primary = _load(DEFAULT_PRIMARY) or {}
    primary_hr = (primary.get("metrics") or {}).get("price_directional_hit_rate")

    wf_identical = (
        apca.get("ngram_pooled_hr") == fabba.get("ngram_pooled_hr")
        and apca.get("ngram_n_evaluated") == fabba.get("ngram_n_evaluated")
        and fabba.get("backend_resolved") == "apca_stub"
    )

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_mutated": False,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "fabba_probe": probe,
        "fabba_native_available": fabba_native,
        "protocol": {
            "last_n_intersection": args.last_n_intersection,
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
            "tol": args.tol,
            "ngram_size": args.ngram_size,
            "lookback": args.lookback,
        },
        "arms": {
            "apca_stub": apca,
            "fabba_requested": fabba,
        },
        "compare": {
            "primary_recommended_chain_hr": primary_hr,
            "apca_ngram_pooled_hr": apca.get("ngram_pooled_hr"),
            "fabba_ngram_pooled_hr": fabba.get("ngram_pooled_hr"),
            "ngram_hr_delta_fabba_minus_apca": round(
                float(fabba["ngram_pooled_hr"]) - float(apca["ngram_pooled_hr"]), 6
            )
            if fabba.get("ngram_pooled_hr") is not None and apca.get("ngram_pooled_hr") is not None
            else None,
            "wf_results_identical_fallback": wf_identical,
            "revalidate_dual_leg_best_hr": (reval or {}).get("dual_leg_revalidated_best", {}).get(
                "pooled_test_directional_hit_rate"
            ),
        },
        "interpretation_ko": [
            "fabba_native_available=false 이면 A/B WF 동일(apca fallback) — Linux에서 재현 필요",
            "Primary 45%와 sidecar ngram HR 합선 금지",
            "Track A merge 금지",
        ],
        "reproduce_linux": (
            "pip install fABBA && py scripts/run_prophecy_fabba_backend_ab_dual_leg_v1.py "
            f"--tol {args.tol} --ngram-size {args.ngram_size}"
        ),
        "reproduce_windows_stub": (
            f"py scripts/run_prophecy_fabba_backend_ab_dual_leg_v1.py "
            f"--tol {args.tol} --ngram-size {args.ngram_size}"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output} fabba_native={fabba_native} "
        f"apca_ngram={apca.get('ngram_pooled_hr')} fabba_ngram={fabba.get('ngram_pooled_hr')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
