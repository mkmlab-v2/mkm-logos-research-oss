#!/usr/bin/env python3
"""Tier-2 lens profile shadow ablation v2 — 180d/2bps + Arm E_dynamic [HYPO].

Extends v1 with:
- harmonized protocol (last-N panel, fee 2bps, neutral 2bps relabel)
- Arm E_dynamic: science+sasang + supplier_tight + dynamic vol veto (Joseph/Babel tol)
- blocked expanding walk-forward on Arms A vs E_dynamic
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402
from scripts.run_prophecy_lens_combo_backtest_v1 import (  # noqa: E402
    _build_expanding_walkforward_blocks,
    _calc_metrics,
    _science_blend_position,
    _sign_to_dir,
)
from scripts.run_prophecy_lens_profile_shadow_ablation_v1 import (  # noqa: E402
    DEFAULT_BTC_CSV,
    DEFAULT_COUNTERFACTUAL,
    DEFAULT_FUSION_ABLATION,
    DEFAULT_SCORE,
    DEFAULT_SCIENCE_JSONL,
    DEFAULT_SIDECAR,
    _arm_e_regime_mkm_split,
    _delta_vs_baseline,
    _extract_science_maps,
    _metrics_summary,
    _prior_completed_daily_return_by_eval_date,
    _read_json,
    _read_json_optional,
    _run_backtest_slice,
    _safe_float,
    _utc_now,
)
from scripts.sasang_regime_mkm_split_v1 import (  # noqa: E402
    build_supplier_regimes_for_dates,
    load_veto_by_date,
    veto_for_date,
)

DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_profile_shadow_ablation_v2_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/prophecy_lens_profile_shadow_ablation_v2_latest.json"
SCHEMA = "prophecy_lens_profile_shadow_ablation_v2"

# [HYPO] dynamic vol veto thresholds (external report proposal; not Track A)
JOSEPH_VOL_THRESH = 0.035
BABEL_VOL_THRESH = 0.020
BABEL_15D_RET_THRESH = 0.08
VOL_LOOKBACK = 5
MOMENTUM_15D = 15


def _neutral_dir(daily_ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if daily_ret > thr:
        return "bull"
    if daily_ret < -thr:
        return "bear"
    return "neutral"


def _relabel_rows_neutral(rows: list[dict[str, Any]], neutral_bps: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        daily_ret = _safe_float(row.get("daily_return"), 0.0)
        row["actual_direction"] = _neutral_dir(daily_ret, neutral_bps)
        out.append(row)
    return out


def _slice_last_n(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    if n <= 0 or len(rows) <= n:
        return list(rows)
    return list(rows[-n:])


def _closes_for_dates(kospi_csv: Path, dates: list[str]) -> dict[str, float]:
    yf_rows = load_kospi_yf_rows(kospi_csv)
    by_date = {str(r["date"])[:10]: float(r["close"]) for r in yf_rows}
    return {d: by_date[d] for d in dates if d in by_date}


def _rolling_vol(rows: list[dict[str, Any]], idx: int, lookback: int) -> float:
    if idx < lookback:
        return 0.0
    rets: list[float] = []
    for j in range(idx - lookback + 1, idx + 1):
        rets.append(_safe_float(rows[j].get("daily_return"), 0.0))
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)
    return math.sqrt(max(0.0, var))


def _logos_era_proxy(closes: dict[str, float], eval_date: str, dates: list[str]) -> str:
    if eval_date not in closes:
        return "JOSEPH"
    try:
        idx = dates.index(eval_date)
    except ValueError:
        return "JOSEPH"
    if idx < MOMENTUM_15D:
        return "JOSEPH"
    d0 = dates[idx - MOMENTUM_15D]
    if d0 not in closes or closes[d0] == 0:
        return "JOSEPH"
    change = closes[eval_date] / closes[d0] - 1.0
    return "BABEL" if change > BABEL_15D_RET_THRESH else "JOSEPH"


def _simulate_arm_e_dynamic(
    *,
    rows: list[dict[str, Any]],
    science_sign_map: dict[str, int],
    science_score_map: dict[str, float],
    myeongni_map: dict[str, int],
    sasang_map: dict[str, int],
    logos_sign: int,
    closes: dict[str, float],
    veto_map: dict[str, bool],
    supplier_map: dict[str, bool],
    fee_rate: float,
    deadzone: float,
    annual_trading_days: int,
) -> dict[str, Any]:
    dates = [str(r.get("eval_date") or "")[:10] for r in rows]
    variant = {
        "science_weight": 0.55,
        "humanist_weight": 0.45,
        "humanist_leg": "sasang",
    }
    prev_pos = 0
    equity = 1.0
    equity_curve: list[float] = []
    pnl_series: list[float] = []
    pred_dirs: list[str] = []
    actual_dirs: list[str] = []
    active_mask: list[bool] = []
    dynamic_veto_days = 0
    blocked_entry_days = 0

    for i, r in enumerate(rows):
        eval_date = str(r.get("eval_date") or "")[:10]
        daily_ret = _safe_float(r.get("daily_return"), 0.0)
        actual_dir = str(r.get("actual_direction") or "neutral").strip().lower()

        base_pos = _science_blend_position(
            eval_date=eval_date,
            variant=variant,
            science_sign_map=science_sign_map,
            science_score_map=science_score_map,
            myeongni_map=myeongni_map,
            sasang_map=sasang_map,
            logos_sign=logos_sign,
            deadzone=deadzone,
        )
        supplier = bool(supplier_map.get(eval_date, False))
        era = _logos_era_proxy(closes, eval_date, dates)
        vol = _rolling_vol(rows, i, VOL_LOOKBACK)
        vol_thresh = JOSEPH_VOL_THRESH if era == "JOSEPH" else BABEL_VOL_THRESH
        dynamic_veto = vol > vol_thresh
        veto = veto_for_date(eval_date, veto_map)

        pos = base_pos
        if not supplier:
            pos = 0
        elif dynamic_veto and base_pos > 0:
            dynamic_veto_days += 1
            pos = 0
        elif veto is True and prev_pos == 0 and base_pos > 0:
            blocked_entry_days += 1
            pos = 0

        turnover = abs(pos - prev_pos)
        fee = turnover * fee_rate
        pnl = (pos * daily_ret) - fee
        equity *= 1.0 + pnl
        prev_pos = pos

        pred_dirs.append(_sign_to_dir(pos))
        actual_dirs.append(actual_dir)
        active_mask.append(pos != 0)
        pnl_series.append(pnl)
        equity_curve.append(equity)

    metrics = _calc_metrics(
        pnl_series=pnl_series,
        equity_series=equity_curve,
        predicted_dirs=pred_dirs,
        actual_dirs=actual_dirs,
        active_mask=active_mask,
        annual_trading_days=annual_trading_days,
    )
    return {
        "strategy_id": "science+sasang+regime_dynamic_veto",
        "arm_id": "E_dynamic",
        "metrics": metrics,
        "gating_stats": {
            "dynamic_veto_days": dynamic_veto_days,
            "blocked_entry_by_force_hold_days": blocked_entry_days,
            "supplier_regime_id": "field_hyst_or_joseph_ext",
            "joseph_vol_thresh": JOSEPH_VOL_THRESH,
            "babel_vol_thresh": BABEL_VOL_THRESH,
        },
    }


def _walkforward_arm_summary(
    *,
    rows: list[dict[str, Any]],
    arm_sim_fn,
    min_train_rows: int,
    test_window_rows: int,
) -> dict[str, Any]:
    blocks = _build_expanding_walkforward_blocks(
        rows,
        min_train_rows=min_train_rows,
        test_window_rows=test_window_rows,
    )
    fold_hits: list[float] = []
    fold_details: list[dict[str, Any]] = []
    for idx, block in enumerate(blocks):
        test_rows = block.get("test_rows") or []
        if not test_rows:
            continue
        result = arm_sim_fn(test_rows)
        m = result.get("metrics") or {}
        hr = float(m.get("directional_hit_rate_active") or 0.0)
        fold_hits.append(hr)
        fold_details.append(
            {
                "fold_index": idx,
                "n_test_rows": len(test_rows),
                "test_date_start": str((test_rows[0] or {}).get("eval_date") or ""),
                "test_date_end": str((test_rows[-1] or {}).get("eval_date") or ""),
                "directional_hit_rate_active": hr,
                "total_return": m.get("total_return"),
                "sharpe": m.get("sharpe"),
            }
        )
    mean_hr = sum(fold_hits) / len(fold_hits) if fold_hits else None
    return {
        "mode": "expanding_blocked_test_only",
        "n_folds_scored": len(fold_hits),
        "mean_test_directional_hit_rate_active": round(mean_hr, 6) if mean_hr is not None else None,
        "folds": fold_details,
    }


def build_ablation_v2(
    *,
    score_json: Path,
    sidecar_json: Path,
    science_jsonl: Path,
    btc_csv: Path,
    kospi_csv: Path,
    sasang_jsonl: Path,
    target_instrument: str,
    eval_days: int,
    fee_bps: float,
    neutral_bps: float,
    deadzone: float,
    logos_min_confidence: float,
    annual_trading_days: int,
    fusion_ablation: Path,
    counterfactual: Path,
    wf_min_train_rows: int,
    wf_test_window_rows: int,
) -> dict[str, Any]:
    score_doc = _read_json(score_json)
    sidecar_doc = _read_json(sidecar_json)
    rows = score_doc.get("rows") or []
    if not isinstance(rows, list):
        raise SystemExit(f"invalid score rows: {score_json}")

    target = str(target_instrument or "kospi").strip().lower()
    filtered = [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == target]
    filtered.sort(key=lambda x: str(x.get("eval_date") or ""))
    filtered = _slice_last_n(filtered, eval_days)
    filtered = _relabel_rows_neutral(filtered, neutral_bps)
    if not filtered:
        raise SystemExit(f"no rows for instrument={target}")

    science_sign_map, science_score_map = _extract_science_maps(science_jsonl)
    btc_prior = _prior_completed_daily_return_by_eval_date(btc_csv) if btc_csv.is_file() else {}
    fee_rate = fee_bps / 10000.0

    omit = _run_backtest_slice(
        rows=filtered,
        sidecar_doc=sidecar_doc,
        science_sign_map=science_sign_map,
        science_score_map=science_score_map,
        btc_prior=btc_prior,
        logos_vote_mode="omit",
        logos_min_confidence=logos_min_confidence,
        fee_rate=fee_rate,
        deadzone=deadzone,
        annual_trading_days=annual_trading_days,
    )
    global_map = _run_backtest_slice(
        rows=filtered,
        sidecar_doc=sidecar_doc,
        science_sign_map=science_sign_map,
        science_score_map=science_score_map,
        btc_prior=btc_prior,
        logos_vote_mode="global",
        logos_min_confidence=logos_min_confidence,
        fee_rate=fee_rate,
        deadzone=deadzone,
        annual_trading_days=annual_trading_days,
    )
    gated = _run_backtest_slice(
        rows=filtered,
        sidecar_doc=sidecar_doc,
        science_sign_map=science_sign_map,
        science_score_map=science_score_map,
        btc_prior=btc_prior,
        logos_vote_mode="confidence_gated",
        logos_min_confidence=logos_min_confidence,
        fee_rate=fee_rate,
        deadzone=deadzone,
        annual_trading_days=annual_trading_days,
    )

    from scripts.run_prophecy_lens_combo_backtest_v1 import _extract_lens_maps

    myeongni_map, sasang_map, logos_sign, logos_confidence = _extract_lens_maps(sidecar_doc)
    dates = [str(r.get("eval_date") or "")[:10] for r in filtered]
    closes = _closes_for_dates(kospi_csv, dates)
    sasang_rows_path = sasang_jsonl
    from scripts.sasang_regime_mkm_split_v1 import load_sasang_rows

    sasang_rows = load_sasang_rows(sasang_rows_path)
    supplier_regimes = build_supplier_regimes_for_dates(closes, dates, sasang_rows)
    supplier_map = supplier_regimes.get("field_hyst_or_joseph_ext") or {}
    veto_map = load_veto_by_date(sasang_jsonl)

    def _sim_e_dyn(test_rows: list[dict[str, Any]]) -> dict[str, Any]:
        test_dates = [str(r.get("eval_date") or "")[:10] for r in test_rows]
        test_closes = _closes_for_dates(kospi_csv, test_dates)
        return _simulate_arm_e_dynamic(
            rows=test_rows,
            science_sign_map=science_sign_map,
            science_score_map=science_score_map,
            myeongni_map=myeongni_map,
            sasang_map=sasang_map,
            logos_sign=logos_sign,
            closes=test_closes,
            veto_map=veto_map,
            supplier_map=supplier_map,
            fee_rate=fee_rate,
            deadzone=deadzone,
            annual_trading_days=annual_trading_days,
        )

    e_dynamic = _sim_e_dyn(filtered)
    baseline = omit["science+sasang"]

    arm_a = {
        "arm_id": "A",
        "label": "science+sasang quant baseline (logos vote omit)",
        "metrics": _metrics_summary(baseline),
    }
    arm_b = {
        "arm_id": "B",
        "label": "science+sasang + Logos sidecar only",
        "metrics": _metrics_summary(baseline),
        "identical_to_arm_a": True,
        "logos_sidecar": {"sign": logos_sign, "confidence": logos_confidence, "non_gating": True},
    }
    triple = omit["science+sasang+myeongni"]
    arm_c = {
        "arm_id": "C",
        "label": "science+sasang vs science+sasang+myeongni",
        "compare": {
            "science+sasang": _metrics_summary(baseline),
            "science+sasang+myeongni": _metrics_summary(triple),
        },
        "delta_triple_vs_baseline": _delta_vs_baseline(baseline, triple),
    }
    arm_d = {
        "arm_id": "D",
        "label": "logos vote mode sensitivity",
        "science+logos_by_mode": {
            "omit": _metrics_summary(omit["science+logos"]),
            "global": _metrics_summary(global_map["science+logos"]),
            "confidence_gated": _metrics_summary(gated["science+logos"]),
        },
        "logos+sasang_by_mode": {
            "omit": _metrics_summary(omit["logos+sasang"]),
            "global": _metrics_summary(global_map["logos+sasang"]),
            "confidence_gated": _metrics_summary(gated["logos+sasang"]),
        },
    }
    arm_e = _arm_e_regime_mkm_split(fusion_ablation, counterfactual)
    arm_e_dynamic = {
        "arm_id": "E_dynamic",
        "label": "science+sasang + supplier_tight + dynamic vol veto (Joseph/Babel tol)",
        "metrics": _metrics_summary(e_dynamic),
        "gating_stats": e_dynamic.get("gating_stats"),
        "delta_vs_arm_a": _delta_vs_baseline(baseline, e_dynamic),
        "note_ko": (
            "[HYPO] KOSPI 패널 방향성 시뮬; 외부 보고 71.3%/Sharpe2.11 미재현 전제. "
            "supplier=field_hyst_or_joseph_ext; veto=추격 진입 차단만."
        ),
    }

    def _sim_a(test_rows: list[dict[str, Any]]) -> dict[str, Any]:
        return _run_backtest_slice(
            rows=test_rows,
            sidecar_doc=sidecar_doc,
            science_sign_map=science_sign_map,
            science_score_map=science_score_map,
            btc_prior=btc_prior,
            logos_vote_mode="omit",
            logos_min_confidence=logos_min_confidence,
            fee_rate=fee_rate,
            deadzone=deadzone,
            annual_trading_days=annual_trading_days,
        )["science+sasang"]

    wf_a = _walkforward_arm_summary(
        rows=filtered,
        arm_sim_fn=_sim_a,
        min_train_rows=wf_min_train_rows,
        test_window_rows=wf_test_window_rows,
    )
    wf_e_dyn = _walkforward_arm_summary(
        rows=filtered,
        arm_sim_fn=_sim_e_dyn,
        min_train_rows=wf_min_train_rows,
        test_window_rows=wf_test_window_rows,
    )

    a_m = arm_a["metrics"]
    e_m = arm_e_dynamic["metrics"]
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "protocol": {
            "protocol_id": "180d_2bps_blocked_wf",
            "eval_days": eval_days,
            "fee_bps": fee_bps,
            "neutral_bps": neutral_bps,
            "walkforward_mode": "expanding",
            "walkforward_min_train_rows": wf_min_train_rows,
            "walkforward_test_window_rows": wf_test_window_rows,
            "date_start": str(filtered[0].get("eval_date") or ""),
            "date_end": str(filtered[-1].get("eval_date") or ""),
            "n_panel_rows": len(filtered),
        },
        "inputs": {
            "score_json": str(score_json),
            "sidecar_json": str(sidecar_json),
            "science_jsonl": str(science_jsonl),
            "kospi_csv": str(kospi_csv),
            "sasang_jsonl": str(sasang_jsonl),
        },
        "arms": {
            "A": arm_a,
            "B": arm_b,
            "C": arm_c,
            "D": arm_d,
            "E": arm_e,
            "E_dynamic": arm_e_dynamic,
        },
        "walkforward": {
            "A_science_sasang": wf_a,
            "E_dynamic": wf_e_dyn,
        },
        "headline_ko": [
            f"A hit={a_m['directional_hit_rate_active']:.1%} sharpe={a_m['sharpe']:.2f} ret={a_m['total_return']:.1%}",
            f"E_dynamic hit={e_m['directional_hit_rate_active']:.1%} sharpe={e_m['sharpe']:.2f} ret={e_m['total_return']:.1%}",
            f"E_dynamic vs A ret Δ={arm_e_dynamic['delta_vs_arm_a']['total_return_delta_pp']:+.1f}pp",
            f"WF mean test HR A={wf_a.get('mean_test_directional_hit_rate_active')} E_dyn={wf_e_dyn.get('mean_test_directional_hit_rate_active')}",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--target-instrument", default="kospi")
    ap.add_argument("--eval-days", type=int, default=180)
    ap.add_argument("--fee-bps", type=float, default=2.0)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--coordinator-deadzone", type=float, default=0.001)
    ap.add_argument("--logos-min-confidence", type=float, default=0.25)
    ap.add_argument("--annual-trading-days", type=int, default=252)
    ap.add_argument("--wf-min-train-rows", type=int, default=30)
    ap.add_argument("--wf-test-window-rows", type=int, default=25)
    ap.add_argument("--fusion-ablation", type=Path, default=DEFAULT_FUSION_ABLATION)
    ap.add_argument("--counterfactual", type=Path, default=DEFAULT_COUNTERFACTUAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    payload = build_ablation_v2(
        score_json=args.score_json,
        sidecar_json=args.sidecar_json,
        science_jsonl=args.science_jsonl,
        btc_csv=args.btc_csv,
        kospi_csv=args.kospi_csv,
        sasang_jsonl=args.sasang_jsonl,
        target_instrument=args.target_instrument,
        eval_days=max(1, int(args.eval_days)),
        fee_bps=float(args.fee_bps),
        neutral_bps=float(args.neutral_bps),
        deadzone=abs(float(args.coordinator_deadzone)),
        logos_min_confidence=float(args.logos_min_confidence),
        annual_trading_days=max(1, int(args.annual_trading_days)),
        fusion_ablation=args.fusion_ablation,
        counterfactual=args.counterfactual,
        wf_min_train_rows=max(2, int(args.wf_min_train_rows)),
        wf_test_window_rows=max(2, int(args.wf_test_window_rows)),
    )

    for path in (args.output, args.artifact_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    e_dyn = payload["arms"]["E_dynamic"]["metrics"]
    print(
        f"OK v2 rows={payload['protocol']['n_panel_rows']} "
        f"A_hit={payload['arms']['A']['metrics']['directional_hit_rate_active']:.3f} "
        f"E_dyn_hit={e_dyn['directional_hit_rate_active']:.3f} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
