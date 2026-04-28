#!/usr/bin/env python3
"""Multi-scenario optimization for role-based lens router (research-only).

Sweeps:
- OOS horizon days
- role-router parameters (regime lookback, neutral cap, strength weights)
- coordinator policies
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SCORE_JSON = ART / "btrack_prophecy_score_pre_causal_active_latest.json"
DEFAULT_SIDECAR_JSON = ART / "btrack_prophecy_score_insight_sidecar_v1_latest.json"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ART / "prophecy_role_router_multiscenario_opt_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _std(values: list[float]) -> float:
    n = len(values)
    if n <= 1:
        return 0.0
    m = sum(values) / n
    return (sum((x - m) ** 2 for x in values) / (n - 1)) ** 0.5


def _prior_completed_daily_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    if len(rows) < 3:
        return out
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[ed] = (c1 - c2) / c2
    return out


def _extract_sidecar_maps(sidecar: dict[str, Any]) -> tuple[dict[str, int], dict[str, int], int]:
    logos_score = (((sidecar.get("lens_globals_for_sidecar") or {}).get("logos") or {}).get("direction_score"))
    logos_sign = _sign(_safe_float(logos_score, 0.0))
    myeongni: dict[str, int] = {}
    sasang: dict[str, int] = {}
    for row in (sidecar.get("per_date_features") or []):
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "")[:10]
        if not ed:
            continue
        dated = row.get("dated_source_snapshots_asof_eval_date") or {}
        m_target = (((dated.get("myeongni_16_state_jsonl") or {}).get("snapshot")) or {}).get("mapping_target")
        s_target = (((dated.get("sasang_dynamics_jsonl") or {}).get("snapshot")) or {}).get("mapping_target")
        m = str(m_target or "neutral").strip().lower()
        s = str(s_target or "neutral").strip().lower()
        myeongni[ed] = 1 if m == "bull" else (-1 if m == "bear" else 0)
        sasang[ed] = 1 if s == "bull" else (-1 if s == "bear" else 0)
    return myeongni, sasang, logos_sign


def _regime(eval_date: str, btc_prior: dict[str, float], logos_sign: int, month_lookback_days: int) -> int:
    keys = sorted([k for k in btc_prior.keys() if k <= eval_date])
    tail = keys[-max(1, month_lookback_days) :]
    if not tail:
        return 0
    avg = sum(btc_prior[k] for k in tail) / len(tail)
    r = _sign(avg)
    if logos_sign == 0:
        return r
    if r != 0 and r != logos_sign:
        return 0
    return logos_sign if r == 0 else r


def _metrics(pnl: list[float], active: list[bool], hit: list[bool], annual_days: int) -> dict[str, Any]:
    n = len(pnl)
    n_active = sum(1 for a in active if a)
    hit_rate = (sum(1 for x in hit if x) / n_active) if n_active else 0.0
    wins = sum(1 for p, a in zip(pnl, active) if a and p > 0)
    win_rate = (wins / n_active) if n_active else 0.0
    eq = 1.0
    curve: list[float] = []
    for p in pnl:
        eq *= (1.0 + p)
        curve.append(eq)
    total = eq - 1.0
    peak = 1.0
    mdd = 0.0
    for v in curve:
        peak = max(peak, v)
        dd = (v / peak) - 1.0 if peak > 0 else 0.0
        mdd = min(mdd, dd)
    avg = (sum(pnl) / n) if n else 0.0
    sd = _std(pnl)
    neg = [x for x in pnl if x < 0]
    downside = _std(neg) if len(neg) > 1 else 0.0
    sharpe = (avg / sd) * (annual_days**0.5) if sd > 0 else 0.0
    sortino = (avg / downside) * (annual_days**0.5) if downside > 0 else 0.0
    years = (n / annual_days) if n else 0.0
    cagr = ((eq ** (1.0 / years)) - 1.0) if years > 0 and eq > 0 else 0.0
    return {
        "n_days": n,
        "n_active_days": n_active,
        "directional_hit_rate_active": round(hit_rate, 6),
        "win_rate_active": round(win_rate, 6),
        "total_return": round(total, 6),
        "cagr": round(cagr, 6),
        "mdd": round(mdd, 6),
        "sharpe": round(sharpe, 6),
        "sortino": round(sortino, 6),
    }


def _run_router(
    rows: list[dict[str, Any]],
    *,
    btc_prior: dict[str, float],
    m_map: dict[str, int],
    s_map: dict[str, int],
    logos_sign: int,
    fee_bps: float,
    month_lookback_days: int,
    neutral_size: float,
    strength_aligned: float,
    strength_neutral: float,
    strength_conflict: float,
    coord_policy: str,
    coord_deadzone: float,
    annual_days: int,
) -> dict[str, Any]:
    fee = fee_bps / 10000.0
    prev_pos = 0.0
    pnl: list[float] = []
    active: list[bool] = []
    hit: list[bool] = []

    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        ret = _safe_float(r.get("daily_return"), 0.0)
        actual = str(r.get("actual_direction") or "neutral").strip().lower()
        actual_sign = 1 if actual == "bull" else (-1 if actual == "bear" else 0)

        reg = _regime(ed, btc_prior, logos_sign, month_lookback_days)
        base = int(m_map.get(ed, 0))
        over = int(s_map.get(ed, 0))
        prior = _safe_float(btc_prior.get(ed), 0.0)
        coord_sign = _sign(prior) if abs(prior) >= coord_deadzone else 0

        if base == 0:
            pos = 0.0
        else:
            if over == base:
                strength = strength_aligned
            elif over == 0:
                strength = strength_neutral
            else:
                strength = strength_conflict
            pos = float(base) * strength

        if coord_policy == "tie_break":
            if base == 0 and coord_sign != 0:
                pos = float(coord_sign) * strength_neutral
        elif coord_policy == "confirm_only":
            if coord_sign != 0 and _sign(pos) != 0 and _sign(pos) != coord_sign:
                pos = 0.0
        elif coord_policy == "regime_transition_only":
            if reg == 0 and coord_sign != 0 and base != 0 and _sign(pos) != coord_sign:
                pos = float(base) * min(strength_neutral, 0.4)

        if reg == 0:
            cap = max(0.0, min(1.0, neutral_size))
            pos = max(-cap, min(cap, pos))
        elif reg > 0:
            pos = max(0.0, pos)
        else:
            pos = min(0.0, pos)

        turnover = abs(pos - prev_pos)
        day_pnl = (pos * ret) - (turnover * fee)
        prev_pos = pos

        pnl.append(day_pnl)
        active_flag = abs(pos) > 1e-12
        active.append(active_flag)
        hit.append(active_flag and (_sign(pos) == actual_sign))

    return _metrics(pnl, active, hit, annual_days)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE_JSON)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR_JSON)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--target-instrument", type=str, default="btc")
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--annual-trading-days", type=int, default=252)
    ap.add_argument("--oos-days-grid", type=str, default="14,21,30")
    ap.add_argument("--month-lookback-grid", type=str, default="14,21,28")
    ap.add_argument("--neutral-size-grid", type=str, default="0.3,0.5,0.7")
    ap.add_argument("--strength-aligned-grid", type=str, default="1.0")
    ap.add_argument("--strength-neutral-grid", type=str, default="0.5,0.6")
    ap.add_argument("--strength-conflict-grid", type=str, default="0.1,0.2,0.3")
    ap.add_argument("--coord-policies", type=str, default="off,tie_break,confirm_only,regime_transition_only")
    ap.add_argument("--coord-deadzone-grid", type=str, default="0.0,0.003,0.005")
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score = _read_json(args.score_json)
    sidecar = _read_json(args.sidecar_json)
    rows = score.get("rows") or []
    if not isinstance(rows, list):
        raise SystemExit(f"invalid rows: {args.score_json}")
    inst = str(args.target_instrument or "btc").strip().lower()
    panel = [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == inst]
    panel.sort(key=lambda x: str(x.get("eval_date") or ""))
    if len(panel) < 20:
        raise SystemExit("not enough rows")

    btc_prior = _prior_completed_daily_return_by_eval_date(args.btc_csv) if args.btc_csv.is_file() else {}
    m_map, s_map, logos_sign = _extract_sidecar_maps(sidecar)
    annual = max(1, int(args.annual_trading_days))

    oos_days_grid = [int(x.strip()) for x in str(args.oos_days_grid).split(",") if x.strip()]
    lookbacks = [int(x.strip()) for x in str(args.month_lookback_grid).split(",") if x.strip()]
    neutral_sizes = [float(x.strip()) for x in str(args.neutral_size_grid).split(",") if x.strip()]
    aligned_grid = [float(x.strip()) for x in str(args.strength_aligned_grid).split(",") if x.strip()]
    neutral_grid = [float(x.strip()) for x in str(args.strength_neutral_grid).split(",") if x.strip()]
    conflict_grid = [float(x.strip()) for x in str(args.strength_conflict_grid).split(",") if x.strip()]
    coord_policies = [x.strip() for x in str(args.coord_policies).split(",") if x.strip()]
    coord_dz_grid = [float(x.strip()) for x in str(args.coord_deadzone_grid).split(",") if x.strip()]

    results: list[dict[str, Any]] = []
    for oos_days in oos_days_grid:
        if oos_days >= len(panel) - 5:
            continue
        train_rows = panel[:-oos_days]
        oos_rows = panel[-oos_days:]
        for lb, nz, sa, sn, sc, cp, cdz in itertools.product(
            lookbacks,
            neutral_sizes,
            aligned_grid,
            neutral_grid,
            conflict_grid,
            coord_policies,
            coord_dz_grid,
        ):
            if not (0.0 <= sc <= sn <= sa <= 1.0):
                continue
            train_m = _run_router(
                train_rows,
                btc_prior=btc_prior,
                m_map=m_map,
                s_map=s_map,
                logos_sign=logos_sign,
                fee_bps=float(args.fee_bps),
                month_lookback_days=lb,
                neutral_size=nz,
                strength_aligned=sa,
                strength_neutral=sn,
                strength_conflict=sc,
                coord_policy=cp,
                coord_deadzone=cdz,
                annual_days=annual,
            )
            oos_m = _run_router(
                oos_rows,
                btc_prior=btc_prior,
                m_map=m_map,
                s_map=s_map,
                logos_sign=logos_sign,
                fee_bps=float(args.fee_bps),
                month_lookback_days=lb,
                neutral_size=nz,
                strength_aligned=sa,
                strength_neutral=sn,
                strength_conflict=sc,
                coord_policy=cp,
                coord_deadzone=cdz,
                annual_days=annual,
            )
            robust_score = (
                (2.0 * float(oos_m.get("mdd") or 0.0))  # less negative is better
                + (1.0 * float(oos_m.get("sharpe") or 0.0))
                + (0.6 * float(oos_m.get("total_return") or 0.0))
                + (0.3 * float(train_m.get("total_return") or 0.0))
            )
            results.append(
                {
                    "oos_days": oos_days,
                    "params": {
                        "month_lookback_days": lb,
                        "neutral_size": nz,
                        "strength_aligned": sa,
                        "strength_neutral": sn,
                        "strength_conflict": sc,
                        "coord_policy": cp,
                        "coord_deadzone": cdz,
                    },
                    "train_metrics": train_m,
                    "oos_metrics": oos_m,
                    "robust_score": round(robust_score, 6),
                }
            )

    ranked = sorted(
        results,
        key=lambda x: (
            float(x.get("robust_score") or -9999.0),
            float((x.get("oos_metrics") or {}).get("mdd") or -999.0),
            float((x.get("oos_metrics") or {}).get("sharpe") or -999.0),
            float((x.get("oos_metrics") or {}).get("total_return") or -999.0),
        ),
        reverse=True,
    )
    top_k = max(1, int(args.top_k))

    out = {
        "schema": "prophecy_role_router_multiscenario_opt_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "sidecar_json": str(args.sidecar_json),
            "btc_csv": str(args.btc_csv),
            "target_instrument": inst,
            "fee_bps": float(args.fee_bps),
            "annual_trading_days": annual,
            "oos_days_grid": oos_days_grid,
            "month_lookback_grid": lookbacks,
            "neutral_size_grid": neutral_sizes,
            "strength_aligned_grid": aligned_grid,
            "strength_neutral_grid": neutral_grid,
            "strength_conflict_grid": conflict_grid,
            "coord_policies": coord_policies,
            "coord_deadzone_grid": coord_dz_grid,
            "total_candidates": len(results),
        },
        "best_candidate": ranked[0] if ranked else None,
        "top_candidates": ranked[:top_k],
        "note": "Rank uses robustness-first objective: MDD defense > Sharpe > OOS return > train support.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if ranked:
        best = ranked[0]
        print(
            f"BEST oos_days={best['oos_days']} robust_score={best['robust_score']} "
            f"oos_mdd={(best['oos_metrics'] or {}).get('mdd')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
