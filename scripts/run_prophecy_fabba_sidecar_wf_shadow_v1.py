#!/usr/bin/env python3
"""[HYPO] Prophecy fABBA symbolic sidecar blocked-WF shadow (B-track, research_only).

Compares last-polygon-slope direction (fABBA or pure-Python APCA stub) against
classical momentum on KOSPI and optional BTC daily panels. Same blocked-WF protocol
as RQ-025 TSFM shadows — no Track A / headline mutation.
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
    NgramPatternLut,
    aggregate_fold_metrics,
    blocked_folds,
    eval_direction_arm,
    fabba_dependency_probe,
    fabba_sidecar_pred,
    mom_pred,
    resolve_backend,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_sidecar_wf_shadow_v1_latest.json"
DEFAULT_FEATURE_LUT_OUT = ROOT / "reports/prophecy_fabba_sidecar_feature_lut_v1_latest.json"
DEFAULT_WF_COMPARE = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
DEFAULT_RQ025 = ROOT / "reports/rq025_tsfm_delta_arms_v1_latest.json"
SCHEMA = "prophecy_fabba_sidecar_wf_shadow_v1"


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


def _load_closes(csv_path: Path) -> list[tuple[str, float]]:
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: list[tuple[str, float]] = []
    for r in rows:
        try:
            out.append((str(r["date"])[:10], float(r["close"])))
        except (TypeError, ValueError, KeyError):
            continue
    return out


def _run_instrument_panel(
    *,
    instrument_id: str,
    csv_path: Path,
    eval_days: int,
    n_folds: int,
    neutral_bps_list: list[float],
    lookback: int,
    ngram_size: int,
    tol: float,
    backend: str,
    alpha: float,
) -> dict[str, Any]:
    if not csv_path.is_file():
        return {"instrument_id": instrument_id, "status": "missing_csv", "csv": str(csv_path)}

    series = _load_closes(csv_path)
    if len(series) < 30:
        return {"instrument_id": instrument_id, "status": "insufficient_rows", "n_rows": len(series)}

    if eval_days > 0:
        series = series[-eval_days:]
    dates = [d for d, _ in series]
    closes = [c for _, c in series]
    date_to_idx = {d: i for i, d in enumerate(dates)}
    folds = blocked_folds(dates, n_folds)
    resolved_backend, backend_meta = resolve_backend(backend)

    nbps_results: list[dict[str, Any]] = []
    for neutral_bps in neutral_bps_list:
        fabba_fold_rows: list[dict[str, Any]] = []
        ngram_fold_rows: list[dict[str, Any]] = []
        mom_fold_rows: list[dict[str, Any]] = []

        for fi, (train, test) in enumerate(folds):
            train_indices = [date_to_idx[d] for d in train if d in date_to_idx]
            ngram_lut = NgramPatternLut()
            ngram_lut.fit(
                closes,
                train_indices,
                lookback=lookback,
                ngram_size=ngram_size,
                tol=tol,
                backend=resolved_backend,
                neutral_bps=neutral_bps,
                alpha=alpha,
            )

            def _fabba_pred(i: int) -> str:
                return fabba_sidecar_pred(
                    closes,
                    i,
                    lookback=lookback,
                    tol=tol,
                    neutral_bps=neutral_bps,
                    backend=resolved_backend,
                )

            def _ngram_pred(i: int) -> str:
                pred, _conf = ngram_lut.predict(
                    closes,
                    i,
                    lookback=lookback,
                    ngram_size=ngram_size,
                    tol=tol,
                    backend=resolved_backend,
                    alpha=alpha,
                )
                return pred

            def _mom_pred(i: int) -> str:
                return mom_pred(closes, i, lookback, neutral_bps)

            fabba_m = eval_direction_arm(
                dates,
                date_to_idx,
                closes,
                test_dates=test,
                neutral_bps=neutral_bps,
                predict_fn=_fabba_pred,
            )
            ngram_m = eval_direction_arm(
                dates,
                date_to_idx,
                closes,
                test_dates=test,
                neutral_bps=neutral_bps,
                predict_fn=_ngram_pred,
            )
            mom_m = eval_direction_arm(
                dates,
                date_to_idx,
                closes,
                test_dates=test,
                neutral_bps=neutral_bps,
                predict_fn=_mom_pred,
            )
            fabba_fold_rows.append({"fold": fi, "test_dates": [test[0], test[-1]], **fabba_m})
            ngram_fold_rows.append(
                {
                    "fold": fi,
                    "test_dates": [test[0], test[-1]],
                    "n_lut_patterns": len(ngram_lut.lut),
                    **ngram_m,
                }
            )
            mom_fold_rows.append({"fold": fi, "test_dates": [test[0], test[-1]], **mom_m})

        fabba_agg = aggregate_fold_metrics(fabba_fold_rows)
        ngram_agg = aggregate_fold_metrics(ngram_fold_rows)
        mom_agg = aggregate_fold_metrics(mom_fold_rows)
        nbps_results.append(
            {
                "neutral_bps": neutral_bps,
                "arms": [
                    {
                        "arm_id": "fabba_sidecar_last_slope",
                        "model": f"symbolic_last_slope_{resolved_backend}",
                        "protocol": "blocked_walkforward_test_only",
                        "lookback_days": lookback,
                        "tol": tol,
                        **fabba_agg,
                        "folds": fabba_fold_rows,
                    },
                    {
                        "arm_id": "fabba_sidecar_ngram_lut",
                        "model": f"symbolic_ngram_lut_{resolved_backend}",
                        "protocol": "blocked_walkforward_test_only",
                        "lookback_days": lookback,
                        "ngram_size": ngram_size,
                        "tol": tol,
                        **ngram_agg,
                        "folds": ngram_fold_rows,
                    },
                    {
                        "arm_id": f"mom_{lookback}d",
                        "model": f"classical_momentum_{lookback}d",
                        "protocol": "blocked_walkforward_test_only",
                        "lookback_days": lookback,
                        **mom_agg,
                        "folds": mom_fold_rows,
                    },
                ],
                "fabba_vs_mom_pooled_pp": round(
                    (fabba_agg.get("pooled_test_directional_hit_rate") or 0.0)
                    - (mom_agg.get("pooled_test_directional_hit_rate") or 0.0),
                    6,
                )
                if fabba_agg.get("pooled_test_directional_hit_rate") is not None
                and mom_agg.get("pooled_test_directional_hit_rate") is not None
                else None,
                "ngram_vs_last_slope_pooled_pp": round(
                    (ngram_agg.get("pooled_test_directional_hit_rate") or 0.0)
                    - (fabba_agg.get("pooled_test_directional_hit_rate") or 0.0),
                    6,
                )
                if ngram_agg.get("pooled_test_directional_hit_rate") is not None
                and fabba_agg.get("pooled_test_directional_hit_rate") is not None
                else None,
            }
        )

    return {
        "instrument_id": instrument_id,
        "status": "ok",
        "csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "window": {
            "eval_days": eval_days,
            "date_from": dates[0],
            "date_to": dates[-1],
            "n_calendar_days": len(dates),
            "n_folds": n_folds,
        },
        "backend_meta": backend_meta,
        "neutral_bps_runs": nbps_results,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--include-btc", action="store_true", help="Also score BTC daily panel")
    ap.add_argument("--eval-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument(
        "--neutral-bps-list",
        default="2.0,5.0",
        help="Comma-separated neutral bps values (default 2.0,5.0 for protocol alignment)",
    )
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--ngram-size", type=int, default=3)
    ap.add_argument("--alpha", type=float, default=0.1, help="fABBA alpha (ignored for apca_stub)")
    ap.add_argument("--tol", type=float, default=0.05, help="APCA/fABBA polygon tolerance (relative)")
    ap.add_argument(
        "--backend",
        choices=("auto", "apca_stub", "fabba"),
        default="auto",
        help="auto=fABBA if installed else apca_stub",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--export-feature-lut",
        action="store_true",
        help="Also write causal sidecar feature_lut JSON (non-gating meta only)",
    )
    ap.add_argument("--feature-lut-output", type=Path, default=DEFAULT_FEATURE_LUT_OUT)
    args = ap.parse_args(argv)

    neutral_bps_list = [float(x.strip()) for x in args.neutral_bps_list.split(",") if x.strip()]
    if not neutral_bps_list:
        print("empty --neutral-bps-list", file=sys.stderr)
        return 2

    panels: list[dict[str, Any]] = []
    kospi = _run_instrument_panel(
        instrument_id="kospi",
        csv_path=args.kospi_csv,
        eval_days=args.eval_days,
        n_folds=args.n_folds,
        neutral_bps_list=neutral_bps_list,
        lookback=args.lookback,
        ngram_size=args.ngram_size,
        tol=args.tol,
        backend=args.backend,
        alpha=args.alpha,
    )
    panels.append(kospi)
    if kospi.get("status") != "ok":
        print(f"kospi panel failed: {kospi.get('status')}", file=sys.stderr)
        return 2

    if args.include_btc:
        panels.append(
            _run_instrument_panel(
                instrument_id="btc",
                csv_path=args.btc_csv,
                eval_days=args.eval_days,
                n_folds=args.n_folds,
                neutral_bps_list=neutral_bps_list,
                lookback=args.lookback,
                ngram_size=args.ngram_size,
                tol=args.tol,
                backend=args.backend,
                alpha=args.alpha,
            )
        )

    wf_compare = _load_json(DEFAULT_WF_COMPARE)
    rq025 = _load_json(DEFAULT_RQ025)
    fabba_probe = fabba_dependency_probe()

    kospi_5bps = next(
        (r for r in kospi.get("neutral_bps_runs", []) if float(r.get("neutral_bps", -1)) == 5.0),
        None,
    )
    fabba_5 = None
    ngram_5 = None
    mom_5 = None
    if kospi_5bps:
        for arm in kospi_5bps.get("arms", []):
            if arm.get("arm_id") == "fabba_sidecar_last_slope":
                fabba_5 = arm
            elif arm.get("arm_id") == "fabba_sidecar_ngram_lut":
                ngram_5 = arm
            elif arm.get("arm_id", "").startswith("mom_"):
                mom_5 = arm

    ensemble_pooled = None
    if wf_compare:
        for arm in (wf_compare.get("blocked_walkforward_test_only") or {}).get("arms") or []:
            if arm.get("arm_id") == "per_date_kospi_ensemble":
                ensemble_pooled = arm.get("pooled_test_directional_hit_rate")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_mutated": False,
        "send_gate": "HOLD",
        "fabba_dependency_probe": fabba_probe,
        "params": {
            "eval_days": args.eval_days,
            "n_folds": args.n_folds,
            "neutral_bps_list": neutral_bps_list,
            "lookback": args.lookback,
            "ngram_size": args.ngram_size,
            "tol": args.tol,
            "alpha": args.alpha,
            "backend_requested": args.backend,
        },
        "panels": panels,
        "compare_pointers": {
            "kospi_wf_holdout_compare": str(DEFAULT_WF_COMPARE.relative_to(ROOT)).replace("\\", "/")
            if wf_compare
            else None,
            "rq025_tsfm_delta_arms": str(DEFAULT_RQ025.relative_to(ROOT)).replace("\\", "/") if rq025 else None,
            "per_date_kospi_ensemble_pooled_hr_252d_5bps": ensemble_pooled,
        },
        "kospi_5bps_summary": {
            "fabba_sidecar_last_slope_pooled_hr": (fabba_5 or {}).get("pooled_test_directional_hit_rate"),
            "fabba_sidecar_ngram_lut_pooled_hr": (ngram_5 or {}).get("pooled_test_directional_hit_rate"),
            "mom_baseline_pooled_hr": (mom_5 or {}).get("pooled_test_directional_hit_rate"),
            "fabba_vs_mom_pooled_pp": (kospi_5bps or {}).get("fabba_vs_mom_pooled_pp"),
            "ngram_vs_last_slope_pooled_pp": (kospi_5bps or {}).get("ngram_vs_last_slope_pooled_pp"),
            "fabba_vs_ensemble_pooled_pp": round(
                (fabba_5 or {}).get("pooled_test_directional_hit_rate", 0.0) - (ensemble_pooled or 0.0),
                6,
            )
            if fabba_5 and fabba_5.get("pooled_test_directional_hit_rate") is not None and ensemble_pooled is not None
            else None,
            "ngram_vs_ensemble_pooled_pp": round(
                (ngram_5 or {}).get("pooled_test_directional_hit_rate", 0.0) - (ensemble_pooled or 0.0),
                6,
            )
            if ngram_5 and ngram_5.get("pooled_test_directional_hit_rate") is not None and ensemble_pooled is not None
            else None,
        },
        "interpretation_ko": [
            "fabba_sidecar_last_slope = last polygon piece slope → bull/bear/neutral (blocked WF OOS).",
            "fabba_sidecar_ngram_lut = train-fold n-gram pattern LUT; LUT reset per fold (no cross-fold leak).",
            "apca_stub = pure Python when fABBA Cython wheel unavailable (Windows default).",
            "neutral_bps 2.0 aligns with recommended eval chain; 5.0 aligns with RQ-025 TSFM table.",
            "feature_lut export = causal per-date meta; non_gating only — Primary score path unchanged.",
            "Track A·headline·Logos 31k gating 자동 교체 없음 — sidecar shadow only.",
        ],
        "reproduce": (
            f"py scripts/run_prophecy_fabba_sidecar_wf_shadow_v1.py --eval-days {args.eval_days} "
            f"--n-folds {args.n_folds} --neutral-bps-list {args.neutral_bps_list}"
            + (" --include-btc" if args.include_btc else "")
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    feature_lut_pointer = None
    if args.export_feature_lut:
        from scripts.prophecy_fabba_sidecar_lib_v1 import build_sidecar_feature_lut_document

        lut_doc = {
            "schema": "prophecy_fabba_sidecar_feature_lut_bundle_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "non_gating": True,
            "send_gate": "HOLD",
            "instruments": [
                build_sidecar_feature_lut_document(
                    instrument_id="kospi",
                    csv_path=args.kospi_csv,
                    generated_at_utc=_utc_now(),
                    lookback=args.lookback,
                    ngram_size=args.ngram_size,
                    tol=args.tol,
                    backend=args.backend,
                    neutral_bps=neutral_bps_list[0],
                    eval_days=args.eval_days,
                    alpha=args.alpha,
                ),
            ],
        }
        if args.include_btc and args.btc_csv.is_file():
            lut_doc["instruments"].append(
                build_sidecar_feature_lut_document(
                    instrument_id="btc",
                    csv_path=args.btc_csv,
                    generated_at_utc=_utc_now(),
                    lookback=args.lookback,
                    ngram_size=args.ngram_size,
                    tol=args.tol,
                    backend=args.backend,
                    neutral_bps=neutral_bps_list[0],
                    eval_days=args.eval_days,
                    alpha=args.alpha,
                )
            )
        args.feature_lut_output.parent.mkdir(parents=True, exist_ok=True)
        args.feature_lut_output.write_text(json.dumps(lut_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        feature_lut_pointer = str(args.feature_lut_output.relative_to(ROOT)).replace("\\", "/")
        out["feature_lut_pointer"] = feature_lut_pointer
        args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"WROTE: {args.output.resolve()} "
        f"kospi_slope_5bps={(fabba_5 or {}).get('pooled_test_directional_hit_rate')} "
        f"kospi_ngram_5bps={(ngram_5 or {}).get('pooled_test_directional_hit_rate')} "
        f"backend={kospi.get('backend_meta', {}).get('backend')}"
        + (f" lut={feature_lut_pointer}" if feature_lut_pointer else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
