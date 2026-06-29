#!/usr/bin/env python3
"""[HYPO] Samsung / semi veto-hold counterfactual vs buy-and-hold (research_only).

Compares eternal-wait, strict force_hold gating, structural-long, and BAH
using yfinance prices + btrack_market_sasang_per_date veto snapshots.
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

from scripts.sasang_regime_mkm_split_v1 import (  # noqa: E402
    DEFAULT_FIELD_EXIT_HYST_DAYS,
    DEFAULT_GEUMHWA_MIN_CONSECUTIVE_DAYS,
    DEFAULT_JOSEPH_END,
    DEFAULT_JOSEPH_START,
    FUSION_POLICY_ARMS,
    RECOMMENDED_REGIME_ID,
    build_supplier_regimes_for_dates,
    daily_fusion_posture,
    load_sasang_rows,
    load_veto_by_date,
    regime_mkm_split_v1,
    veto_for_date,
)

_load_sasang_rows = load_sasang_rows
_load_veto_by_date = load_veto_by_date
_veto_for_date = veto_for_date
_regime_mkm_split_v1 = regime_mkm_split_v1

DEFAULT_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/samsung_sasang_veto_hold_counterfactual_v1_latest.json"
SCHEMA = "samsung_sasang_veto_hold_counterfactual_v1_3"

TICKERS = {
    "samsung": "005930.KS",
    "hynix": "000660.KS",
    "kospi": "^KS11",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _attach_underperform(strategies: dict[str, Any]) -> None:
    bah = strategies.get("buy_and_hold", {}).get("total_return_pct")
    if bah is None:
        return
    for name, strat in strategies.items():
        if name == "buy_and_hold" or not isinstance(strat, dict):
            continue
        tr = strat.get("total_return_pct")
        if tr is not None:
            strat["underperform_vs_bah_pp"] = round(tr - bah, 4)


def _regime_bundle(
    closes: dict[str, float],
    dates: list[str],
    veto_map: dict[str, bool],
    supplier_regimes: dict[str, dict[str, bool]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for regime_id, sup in supplier_regimes.items():
        tight_pct = round(100.0 * sum(1 for d in dates if sup.get(d)) / len(dates), 2) if dates else 0.0
        out[regime_id] = {
            "supplier_tight_pct": tight_pct,
            "regime_mkm_split_v1_tactical": _regime_mkm_split_v1(
                closes, dates, veto_map, sup, structural_entry=False
            ),
            "regime_mkm_split_v1_structural_entry": _regime_mkm_split_v1(
                closes, dates, veto_map, sup, structural_entry=True
            ),
        }
        for key in ("regime_mkm_split_v1_tactical", "regime_mkm_split_v1_structural_entry"):
            tr = out[regime_id][key].get("total_return_pct")
            bah = _bah_return(closes, dates).get("total_return_pct")
            if tr is not None and bah is not None:
                out[regime_id][key]["underperform_vs_bah_pp"] = round(tr - bah, 4)
    return out


def _fetch_closes(ticker: str, period: str = "1y") -> dict[str, float]:
    import yfinance as yf

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True).dropna()
    if df.empty:
        raise RuntimeError(f"no history for {ticker}")
    return {idx.date().isoformat(): float(row["Close"]) for idx, row in df.iterrows()}


def _sorted_dates(closes: dict[str, float]) -> list[str]:
    return sorted(closes.keys())


def _return_pct(p0: float, p1: float) -> float | None:
    if p0 <= 0:
        return None
    return round((p1 / p0 - 1.0) * 100.0, 4)


def _window_slice(dates: list[str], start: str, end: str) -> list[str]:
    return [d for d in dates if start <= d <= end]


def _bah_return(closes: dict[str, float], dates: list[str]) -> dict[str, Any]:
    if len(dates) < 2:
        return {"status": "insufficient", "total_return_pct": None}
    p0 = closes[dates[0]]
    p1 = closes[dates[-1]]
    return {
        "status": "ok",
        "entry_date": dates[0],
        "exit_date": dates[-1],
        "n_trading_days": len(dates),
        "total_return_pct": _return_pct(p0, p1),
    }


def _cash_return() -> dict[str, Any]:
    return {
        "status": "ok",
        "total_return_pct": 0.0,
        "note_ko": "eternal wait / 현금 100%",
    }


def _strict_veto_daily(closes: dict[str, float], dates: list[str], veto_map: dict[str, bool]) -> dict[str, Any]:
    """In market when force_hold=false; cash when true or unknown."""
    if len(dates) < 2:
        return {"status": "insufficient", "total_return_pct": None}
    equity = 1.0
    in_market = False
    entry_price: float | None = None
    trades = 0
    hold_days = 0
    cash_days = 0
    unknown_days = 0
    for d in dates:
        v = _veto_for_date(d, veto_map)
        if v is None:
            unknown_days += 1
            if in_market:
                hold_days += 1
            else:
                cash_days += 1
            continue
        if v:
            if in_market and entry_price is not None:
                equity *= closes[d] / entry_price
                in_market = False
                entry_price = None
                trades += 1
            cash_days += 1
        else:
            if not in_market:
                entry_price = closes[d]
                in_market = True
                trades += 1
            hold_days += 1
    if in_market and entry_price is not None:
        equity *= closes[dates[-1]] / entry_price
    return {
        "status": "ok",
        "total_return_pct": round((equity - 1.0) * 100.0, 4),
        "trades": trades,
        "days_in_market": hold_days,
        "days_in_cash": cash_days,
        "days_veto_unknown": unknown_days,
        "note_ko": "force_hold=true → 현금; false → 보유 (일간 리밸런스)",
    }


def _wait_first_clear_then_hold(closes: dict[str, float], dates: list[str], veto_map: dict[str, bool]) -> dict[str, Any]:
    entry: str | None = None
    for d in dates:
        v = _veto_for_date(d, veto_map)
        if v is False:
            entry = d
            break
    if entry is None:
        return {"status": "never_entered", "total_return_pct": 0.0, "note_ko": "veto가 끝나지 않아 미진입"}
    p0 = closes[entry]
    p1 = closes[dates[-1]]
    return {
        "status": "ok",
        "entry_date": entry,
        "exit_date": dates[-1],
        "total_return_pct": _return_pct(p0, p1),
        "note_ko": "첫 force_hold=false 날 진입 후 보유",
    }


def _structural_long_ignore_veto(closes: dict[str, float], dates: list[str]) -> dict[str, Any]:
    return {
        **_bah_return(closes, dates),
        "note_ko": "Joseph/Field structural long — veto 무시 BAH",
    }


def _tactical_no_chase(closes: dict[str, float], dates: list[str], veto_map: dict[str, bool]) -> dict[str, Any]:
    """Enter on first day; veto days block ADD only — never sell (no chase on veto)."""
    if len(dates) < 2:
        return {"status": "insufficient", "total_return_pct": None}
    # Same as BAH once entered day 1 — documents that hold-through-veto = BAH
    r = _bah_return(closes, dates)
    veto_days = sum(1 for d in dates if _veto_for_date(d, veto_map) is True)
    r["note_ko"] = "구조적 보유(첫날 진입) + veto는 매도 신호 아님 — BAH와 동일"
    r["veto_days_in_window"] = veto_days
    return r


def run_analysis(
    *,
    sasang_path: Path,
    period: str,
    out_path: Path,
) -> dict[str, Any]:
    veto_map = _load_veto_by_date(sasang_path)
    sasang_rows = _load_sasang_rows(sasang_path)
    sasang_dates = sorted(veto_map.keys())
    sasang_start = sasang_dates[0] if sasang_dates else None
    sasang_end = sasang_dates[-1] if sasang_dates else None
    veto_true = sum(1 for v in veto_map.values() if v)
    veto_false = sum(1 for v in veto_map.values() if not v)

    instruments: dict[str, Any] = {}
    for key, ticker in TICKERS.items():
        closes = _fetch_closes(ticker, period=period)
        all_dates = _sorted_dates(closes)
        win_1y = all_dates
        win_sasang = (
            _window_slice(all_dates, sasang_start, sasang_end)
            if sasang_start and sasang_end
            else []
        )

        strategies_1y: dict[str, Any] = {
            "buy_and_hold": _bah_return(closes, win_1y),
            "eternal_cash_wait": _cash_return(),
            "structural_long_bah": _structural_long_ignore_veto(closes, win_1y),
        }
        if win_sasang:
            strategies_sasang = {
                "buy_and_hold": _bah_return(closes, win_sasang),
                "eternal_cash_wait": _cash_return(),
                "strict_veto_daily": _strict_veto_daily(closes, win_sasang, veto_map),
                "first_clear_then_hold": _wait_first_clear_then_hold(closes, win_sasang, veto_map),
                "structural_long_bah": _structural_long_ignore_veto(closes, win_sasang),
                "tactical_hold_through_veto": _tactical_no_chase(closes, win_sasang, veto_map),
            }
            bah_s = strategies_sasang["buy_and_hold"].get("total_return_pct")
            for name, strat in strategies_sasang.items():
                tr = strat.get("total_return_pct")
                if bah_s is not None and tr is not None and name != "buy_and_hold":
                    strat["underperform_vs_bah_pp"] = round(tr - bah_s, 4)

        else:
            strategies_sasang = {"status": "no_overlap_with_sasang_window"}

        bah_1y = strategies_1y["buy_and_hold"].get("total_return_pct")
        cash_1y = strategies_1y["eternal_cash_wait"].get("total_return_pct")
        if bah_1y is not None and cash_1y is not None:
            strategies_1y["eternal_cash_wait"]["underperform_vs_bah_pp"] = round(cash_1y - bah_1y, 4)

        regimes_1y = build_supplier_regimes_for_dates(closes, win_1y, sasang_rows)
        regime_conditional_1y = _regime_bundle(closes, win_1y, veto_map, regimes_1y)

        regime_conditional_sasang: dict[str, Any] = {"status": "no_overlap_with_sasang_window"}
        if win_sasang:
            regimes_s = build_supplier_regimes_for_dates(closes, win_sasang, sasang_rows)
            regime_conditional_sasang = _regime_bundle(closes, win_sasang, veto_map, regimes_s)

        instruments[key] = {
            "ticker": ticker,
            "price_window_1y": {"start": win_1y[0], "end": win_1y[-1], "n_days": len(win_1y)},
            "strategies_1y": strategies_1y,
            "regime_conditional_1y": regime_conditional_1y,
            "sasang_veto_window": {"start": sasang_start, "end": sasang_end, "eval_rows": len(veto_map)},
            "strategies_sasang_window": strategies_sasang,
            "regime_conditional_sasang_window": regime_conditional_sasang,
        }

    doc = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "purpose_ko": "veto narrative vs BAH + regime-conditional MKM split (supplier_tight × tactical veto)",
        "regime_definitions_ko": {
            "field_momentum_sma60": "종가>SMA60 & 20d 수익률>0",
            "field_momentum_sma60_hyst10": "field + 10일 연속 tight=false 확인 후 청산 (whipsaw 완화)",
            "geumhwa_execution": "heat×(1-cold)≥0.35 (machine_readables; sparse)",
            "geumhwa_execution_gated5": "geumhwa + 5일 연속 True 확인 (sparse overfit 완화)",
            "joseph_calendar_2026_2028": "Joseph fat narrative 2026-01-01..2028",
            "joseph_calendar_2025_06_2028": "Joseph extended 2025-06-01..2028 (1Y 백필)",
            "field_or_joseph_legacy": "field OR joseph_2026 (legacy 1Y composite)",
            "field_hyst_or_joseph_ext": "field_hyst10 OR joseph_2025_06 (권장 composite)",
            "regime_mkm_split_v1_tactical": "tight=롱; veto=신규진입만 차단; tight 해제시 청산",
            "regime_mkm_split_v1_structural_entry": "tight 첫날 진입(veto 무시); tight 해제시 청산",
        },
        "regime_params": {
            "joseph_start": DEFAULT_JOSEPH_START,
            "joseph_end": DEFAULT_JOSEPH_END,
            "field_exit_hysteresis_days": DEFAULT_FIELD_EXIT_HYST_DAYS,
            "geumhwa_min_consecutive_days": DEFAULT_GEUMHWA_MIN_CONSECUTIVE_DAYS,
            "recommended_regime_id": RECOMMENDED_REGIME_ID,
        },
        "inputs": {
            "sasang_per_date": str(sasang_path.relative_to(ROOT)).replace("\\", "/"),
            "yfinance_period": period,
            "veto_summary": {
                "force_hold_true": veto_true,
                "force_hold_false": veto_false,
                "force_hold_true_pct": round(100.0 * veto_true / len(veto_map), 2) if veto_map else None,
            },
        },
        "headline_ko": [],
        "instruments": instruments,
        "interpretation_ko": [
            "eternal_cash_wait = 제미나이식 「관망」 1년 — BAH 대비 opportunity cost",
            "strict_veto_daily = force_hold를 매도/현금 신호로 literal 적용 — 과잉 방어",
            "structural_long_bah = Field/Joseph 축 — veto와 분리한 롱",
            "tactical_hold_through_veto = veto는 추격 금지·매도 아님 — 슈퍼사이클에서 BAH와 동일",
            "regime_mkm_split_v1 = supplier_tight(Field/Joseph)와 sasang veto 분리 — generic 관망 탈피",
            "field_hyst10 + joseph_2025-06 = 1Y whipsaw·백필 gap 완화 composite",
        ],
        "reproduce": f"py scripts/run_samsung_sasang_veto_hold_counterfactual_v1.py --period {period}",
    }

    ss = instruments.get("samsung", {})
    s1 = ss.get("strategies_1y", {})
    bah = s1.get("buy_and_hold", {}).get("total_return_pct")
    cash = s1.get("eternal_cash_wait", {}).get("underperform_vs_bah_pp")
    if bah is not None and cash is not None:
        doc["headline_ko"].append(
            f"삼성 1Y BAH +{bah}% vs eternal wait {cash}pp (현금 0%)"
        )
    sw = ss.get("strategies_sasang_window", {})
    if isinstance(sw, dict) and sw.get("strict_veto_daily"):
        sv = sw["strict_veto_daily"]
        doc["headline_ko"].append(
            f"2026 sasang창 strict_veto_daily {sv.get('total_return_pct')}% "
            f"(BAH {sw.get('buy_and_hold', {}).get('total_return_pct')}%, "
            f"underperform {sv.get('underperform_vs_bah_pp')}pp)"
        )
    rc = ss.get("regime_conditional_1y", {})
    if isinstance(rc, dict):
        legacy = rc.get("field_or_joseph_legacy", {})
        if legacy:
            tac_l = legacy.get("regime_mkm_split_v1_tactical", {})
            doc["headline_ko"].append(
                f"1Y legacy (field|joseph2026) tactical {tac_l.get('total_return_pct')}% "
                f"vs BAH {bah}% (underperform {tac_l.get('underperform_vs_bah_pp')}pp)"
            )
        improved = rc.get("field_hyst_or_joseph_ext", {})
        if improved:
            tac_i = improved.get("regime_mkm_split_v1_tactical", {})
            doc["headline_ko"].append(
                f"1Y improved (field_hyst10|joseph2025-06) tactical {tac_i.get('total_return_pct')}% "
                f"vs BAH {bah}% (underperform {tac_i.get('underperform_vs_bah_pp')}pp)"
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--period", default="1y")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    sasang = args.sasang_jsonl if args.sasang_jsonl.is_absolute() else ROOT / args.sasang_jsonl
    out = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        doc = run_analysis(sasang_path=sasang, period=args.period, out_path=out)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"WROTE: {out}")
    for line in doc.get("headline_ko") or []:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
