#!/usr/bin/env python3
"""Role-based lens router backtest (research-only).

Lens role mapping:
- Logos: regime gate (slow/monthly bias proxy)
- Myeongni: base directional signal (medium horizon)
- Sasang: position sizing overlay (short-horizon sentiment proxy)
"""
from __future__ import annotations

import argparse
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
DEFAULT_OUT = ART / "prophecy_lens_role_router_backtest_v1_latest.json"


def _utc_now() -> str:
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
        m_map = str(m_target or "neutral").strip().lower()
        s_map = str(s_target or "neutral").strip().lower()
        myeongni[ed] = 1 if m_map == "bull" else (-1 if m_map == "bear" else 0)
        sasang[ed] = 1 if s_map == "bull" else (-1 if s_map == "bear" else 0)
    return myeongni, sasang, logos_sign


def _regime_for_day(
    *,
    eval_date: str,
    btc_prior: dict[str, float],
    logos_sign: int,
    month_lookback_days: int,
) -> int:
    # Slow regime proxy: month-to-date trailing average prior return with logos polarity.
    keys = sorted([k for k in btc_prior.keys() if k <= eval_date])
    tail = keys[-max(1, month_lookback_days) :]
    if not tail:
        return 0
    avg = sum(btc_prior[k] for k in tail) / len(tail)
    regime = _sign(avg)
    if logos_sign == 0:
        return regime
    # Logos acts as structural filter; disagreement downgrades to neutral.
    if regime != 0 and regime != logos_sign:
        return 0
    if regime == 0:
        return logos_sign
    return regime


def _metrics(
    *,
    pnl: list[float],
    active: list[bool],
    hit: list[bool],
    annual_days: int,
) -> dict[str, Any]:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE_JSON)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR_JSON)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--target-instrument", type=str, default="btc")
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--annual-trading-days", type=int, default=252)
    ap.add_argument("--month-lookback-days", type=int, default=21)
    ap.add_argument("--neutral_size", type=float, default=0.5, help="Size cap in neutral regime.")
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
    if not panel:
        raise SystemExit(f"no rows for instrument={inst}")

    btc_prior = _prior_completed_daily_return_by_eval_date(args.btc_csv) if args.btc_csv.is_file() else {}
    m_map, s_map, logos_sign = _extract_sidecar_maps(sidecar)
    fee = float(args.fee_bps) / 10000.0

    prev_pos = 0.0
    pnl: list[float] = []
    active: list[bool] = []
    hit: list[bool] = []
    trace: list[dict[str, Any]] = []

    for r in panel:
        ed = str(r.get("eval_date") or "")[:10]
        ret = _safe_float(r.get("daily_return"), 0.0)
        actual = str(r.get("actual_direction") or "neutral").strip().lower()
        actual_sign = 1 if actual == "bull" else (-1 if actual == "bear" else 0)

        regime = _regime_for_day(
            eval_date=ed,
            btc_prior=btc_prior,
            logos_sign=logos_sign,
            month_lookback_days=max(5, int(args.month_lookback_days)),
        )
        base = int(m_map.get(ed, 0))  # Myeongni
        over = int(s_map.get(ed, 0))  # Sasang

        if base == 0:
            pos_target = 0.0
        else:
            if over == base:
                strength = 1.0
            elif over == 0:
                strength = 0.6
            else:
                strength = 0.2
            pos_target = float(base) * strength

        # Logos regime gate (slow filter)
        if regime == 0:
            cap = max(0.0, min(1.0, float(args.neutral_size)))
            pos_target = max(-cap, min(cap, pos_target))
        elif regime > 0:
            pos_target = max(0.0, pos_target)  # long-only in risk-on
        else:
            pos_target = min(0.0, pos_target)  # short-only in risk-off

        turnover = abs(pos_target - prev_pos)
        day_pnl = (pos_target * ret) - (turnover * fee)
        prev_pos = pos_target

        pnl.append(day_pnl)
        active_flag = abs(pos_target) > 1e-12
        active.append(active_flag)
        hit.append(active_flag and (_sign(pos_target) == actual_sign))
        trace.append(
            {
                "eval_date": ed,
                "regime_sign": regime,
                "myeongni_sign": base,
                "sasang_sign": over,
                "position": round(pos_target, 6),
                "actual_direction": actual,
                "daily_return": ret,
                "pnl": round(day_pnl, 8),
            }
        )

    out = {
        "schema": "prophecy_lens_role_router_backtest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "sidecar_json": str(args.sidecar_json),
            "btc_csv": str(args.btc_csv),
            "target_instrument": inst,
            "fee_bps": float(args.fee_bps),
            "month_lookback_days": int(args.month_lookback_days),
            "neutral_size": float(args.neutral_size),
            "annual_trading_days": int(args.annual_trading_days),
        },
        "role_mapping": {
            "logos": "slow_regime_gate",
            "myeongni": "base_direction",
            "sasang": "position_strength_overlay",
        },
        "metrics": _metrics(pnl=pnl, active=active, hit=hit, annual_days=max(1, int(args.annual_trading_days))),
        "daily_trace": trace,
        "note": (
            "Role-based experimental harness: logos regime uses slow monthly proxy from prior BTC returns + logos global sign."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"cagr={(out.get('metrics') or {}).get('cagr')} mdd={(out.get('metrics') or {}).get('mdd')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
