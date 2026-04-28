#!/usr/bin/env python3
"""Strict OOS gate for role-based lens router (research-only).

Process:
1) Split panel into train/OOS tail window
2) Fit router params on train only (grid search)
3) Evaluate frozen params on OOS only
4) Emit GO/HOLD gate artifact
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
DEFAULT_OUT = ART / "prophecy_lens_role_router_oos_gate_v1_latest.json"


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

        if base == 0:
            pos = 0.0
        else:
            strength = 1.0 if over == base else (0.6 if over == 0 else 0.2)
            pos = float(base) * strength

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
    ap.add_argument("--oos-tail-days", type=int, default=7)
    ap.add_argument("--month-lookback-grid", type=str, default="14,21,28")
    ap.add_argument("--neutral-size-grid", type=str, default="0.3,0.5,0.7")
    ap.add_argument("--gate-min-hit-rate", type=float, default=0.55)
    ap.add_argument("--gate-max-mdd", type=float, default=-0.12)
    ap.add_argument("--gate-min-sharpe", type=float, default=0.0)
    ap.add_argument("--gate-min-total-return", type=float, default=0.0)
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
    if len(panel) < 12:
        raise SystemExit("not enough rows for strict OOS split")

    oos_tail = max(3, int(args.oos_tail_days))
    if oos_tail >= len(panel):
        raise SystemExit("oos_tail_days too large")
    train_rows = panel[:-oos_tail]
    oos_rows = panel[-oos_tail:]

    btc_prior = _prior_completed_daily_return_by_eval_date(args.btc_csv) if args.btc_csv.is_file() else {}
    m_map, s_map, logos_sign = _extract_sidecar_maps(sidecar)
    annual = max(1, int(args.annual_trading_days))
    lookbacks = [int(x.strip()) for x in str(args.month_lookback_grid).split(",") if x.strip()]
    neutral_sizes = [float(x.strip()) for x in str(args.neutral_size_grid).split(",") if x.strip()]

    candidates: list[dict[str, Any]] = []
    for lb, nz in itertools.product(lookbacks, neutral_sizes):
        train_m = _run_router(
            train_rows,
            btc_prior=btc_prior,
            m_map=m_map,
            s_map=s_map,
            logos_sign=logos_sign,
            fee_bps=float(args.fee_bps),
            month_lookback_days=lb,
            neutral_size=nz,
            annual_days=annual,
        )
        candidates.append({"params": {"month_lookback_days": lb, "neutral_size": nz}, "train_metrics": train_m})

    ranked_train = sorted(
        candidates,
        key=lambda x: (
            float((x.get("train_metrics") or {}).get("sharpe") or -999.0),
            float((x.get("train_metrics") or {}).get("cagr") or -999.0),
            float((x.get("train_metrics") or {}).get("mdd") or -999.0),
        ),
        reverse=True,
    )
    best = ranked_train[0]
    best_params = best["params"]
    oos_m = _run_router(
        oos_rows,
        btc_prior=btc_prior,
        m_map=m_map,
        s_map=s_map,
        logos_sign=logos_sign,
        fee_bps=float(args.fee_bps),
        month_lookback_days=int(best_params["month_lookback_days"]),
        neutral_size=float(best_params["neutral_size"]),
        annual_days=annual,
    )

    checks = {
        "oos_hit_rate_pass": float(oos_m.get("directional_hit_rate_active") or 0.0) >= float(args.gate_min_hit_rate),
        "oos_mdd_pass": float(oos_m.get("mdd") or 0.0) >= float(args.gate_max_mdd),
        "oos_sharpe_pass": float(oos_m.get("sharpe") or 0.0) >= float(args.gate_min_sharpe),
        "oos_total_return_pass": float(oos_m.get("total_return") or 0.0) >= float(args.gate_min_total_return),
    }
    go = all(checks.values())

    out = {
        "schema": "prophecy_lens_role_router_oos_gate_v1",
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
            "oos_tail_days": oos_tail,
            "month_lookback_grid": lookbacks,
            "neutral_size_grid": neutral_sizes,
        },
        "split": {
            "train_rows": len(train_rows),
            "oos_rows": len(oos_rows),
            "train_start": str((train_rows[0] or {}).get("eval_date") or ""),
            "train_end": str((train_rows[-1] or {}).get("eval_date") or ""),
            "oos_start": str((oos_rows[0] or {}).get("eval_date") or ""),
            "oos_end": str((oos_rows[-1] or {}).get("eval_date") or ""),
        },
        "best_train_candidate": best,
        "oos_metrics": oos_m,
        "gate": {
            "go": go,
            "status": "GO_OOS_PASS" if go else "HOLD_OOS_FAIL",
            "checks": checks,
            "thresholds": {
                "min_hit_rate": float(args.gate_min_hit_rate),
                "max_mdd_floor": float(args.gate_max_mdd),
                "min_sharpe": float(args.gate_min_sharpe),
                "min_total_return": float(args.gate_min_total_return),
            },
        },
        "note": "Strict OOS: parameters chosen on train only, then frozen for tail-window evaluation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"gate_status={out['gate']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
