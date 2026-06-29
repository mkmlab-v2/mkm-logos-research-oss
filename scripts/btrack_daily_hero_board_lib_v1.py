#!/usr/bin/env python3
"""B-track daily hero board — 5-slot predict/score helpers [HYPO][research_only]."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/commander/btrack_daily_hero_board_v1.json"
KOSPI_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
KOSPI_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
FLOW_CSV = ROOT / "research/market_data/kospi_daily_flow_external.csv"
FX_CSV = ROOT / "research/market_data/usdkrw_daily_external_yf.csv"
WEATHER_JSONL_HERO = ROOT / "research/market_data/seoul_weather_ground_truth_hero_board.jsonl"
WEATHER_JSONL_SAMPLE = ROOT / "tests/fixtures/weather_ground_truth_rows_v1.sample.jsonl"
PRE_NEWS = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"
NEWS_LENS = ROOT / "docs/final/artifacts/news_independent_lens_latest.json"
MACRO_LENS = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"

MACRO_SHOCK_EN = frozenset(
    "cpi fomc fed tariff sanction war crisis crash plunge shock inflation rate hike cut recession selloff".split()
)
MACRO_SHOCK_KO = frozenset("환율 금리 관세 지정학 긴축 인플레 쇼크 급락 급등 위기 전쟁 제재".split())

NEUTRAL_BPS = 5.0


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clamp01(x: float) -> float:
    return max(0.05, min(0.95, float(x)))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_config() -> dict[str, Any]:
    return _read_json(CONFIG)


def _slot_cfg(slot_id: str) -> dict[str, Any]:
    for s in _load_config().get("slots") or []:
        if isinstance(s, dict) and s.get("slot_id") == slot_id:
            return s
    return {}


def _direction_from_return(ret: float, neutral_bps: float = NEUTRAL_BPS) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _outcome(pred: str, actual: str) -> str:
    if actual == "neutral" or pred == "neutral":
        return "NEUTRAL_DRAW"
    return "HIT" if pred == actual else "FAIL"


def _load_closes_csv(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("Date") or row.get("date") or "")[:10]
            raw = row.get("Close") or row.get("close")
            if len(dk) == 10 and raw not in (None, ""):
                try:
                    out[dk] = float(raw)
                except (ValueError, TypeError):
                    pass
    return out


def _load_flow_by_date(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("date") or "")[:10]
            if len(dk) != 10:
                continue
            entry: dict[str, Any] = {"date": dk}
            for col in ("foreign_net_buy", "institution_net_buy", "program_net_buy"):
                raw = row.get(col)
                if raw not in (None, ""):
                    try:
                        entry[col] = float(raw)
                    except (ValueError, TypeError):
                        entry[col] = None
                else:
                    entry[col] = None
            out[dk] = entry
    return out


def _weather_threshold_mm() -> float:
    return float(_slot_cfg("weather_seoul").get("threshold_mm") or 5.0)


def _weather_jsonl_paths() -> list[Path]:
    cfg = _slot_cfg("weather_seoul")
    paths: list[Path] = []
    for key in ("weather_jsonl", "weather_jsonl_fallback"):
        raw = cfg.get(key)
        if raw:
            paths.append(ROOT / str(raw))
    if not paths:
        paths = [WEATHER_JSONL_HERO, WEATHER_JSONL_SAMPLE]
    return paths


def _load_weather_gt(path: Path, *, threshold_mm: float) -> dict[str, bool]:
    out: dict[str, bool] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        dk = str(row.get("obs_date") or row.get("date") or row.get("observation_date_local") or "")[:10]
        if len(dk) != 10:
            continue
        precip = row.get("precip_mm")
        if precip is None:
            precip = row.get("precipitation_mm")
        if precip is None:
            precip = row.get("precip_mm_day")
        if precip is None and row.get("precip_binary_ge_threshold") is not None:
            out[dk] = bool(row.get("precip_binary_ge_threshold"))
            continue
        try:
            out[dk] = float(precip or 0) >= threshold_mm
        except (ValueError, TypeError):
            continue
    return out


def _merge_weather_gt() -> dict[str, bool]:
    thr = _weather_threshold_mm()
    merged: dict[str, bool] = {}
    for path in reversed(_weather_jsonl_paths()):
        merged.update(_load_weather_gt(path, threshold_mm=thr))
    return merged


def _macro_bias() -> float:
    doc = _read_json(MACRO_LENS)
    d = str(doc.get("direction") or doc.get("predicted_direction") or "neutral").lower()
    s = float(doc.get("score") or doc.get("weighted_score") or 0.0)
    if d == "bull":
        return 0.08 + s * 0.1
    if d == "bear":
        return -0.08 + s * 0.1
    return s * 0.05


def _pre_news_shock_meta() -> dict[str, Any]:
    doc = _read_json(PRE_NEWS)
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    macro_hits = 0
    bear_hits = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        h = str(row.get("headline") or row.get("title") or "")
        h_low = h.lower()
        tok = set(h_low.split())
        if any(k in h_low for k in MACRO_SHOCK_KO) or any(k in tok for k in MACRO_SHOCK_EN):
            macro_hits += 1
        if any(w in h_low for w in ("급락", "폭락", "쇼크", "위기", "crash", "plunge", "shock", "crisis")):
            bear_hits += 1
    return {
        "pre_news_rows": len(rows),
        "macro_keyword_hits": macro_hits,
        "bear_keyword_hits": bear_hits,
        "pre_news_available": bool(rows),
    }


def _news_shock_prob() -> tuple[float, dict[str, Any]]:
    doc = _read_json(NEWS_LENS)
    d = str(doc.get("direction") or "neutral").lower()
    conf = float(doc.get("confidence") or 0.5)
    base = 0.25
    if d == "bear":
        p = base + 0.25 * conf
    elif d == "bull":
        p = base - 0.1 * conf
    else:
        p = base

    meta = _pre_news_shock_meta()
    if meta.get("pre_news_available"):
        boost = min(0.35, 0.04 * float(meta.get("macro_keyword_hits") or 0) + 0.03 * float(meta.get("bear_keyword_hits") or 0))
        p += boost
        meta["pre_news_boost"] = round(boost, 4)
    return clamp01(p), meta


@dataclass
class BoardContext:
    kospi_cal: dict[str, Any]
    kospi_eval: dict[str, Any]
    flow_by_date: dict[str, dict[str, Any]]
    fx_closes: dict[str, float]
    kospi_closes: dict[str, float]
    weather_gt: dict[str, bool]


def load_context() -> BoardContext:
    return BoardContext(
        kospi_cal=_read_json(KOSPI_CAL),
        kospi_eval=_read_json(KOSPI_EVAL),
        flow_by_date=_load_flow_by_date(FLOW_CSV),
        fx_closes=_load_closes_csv(FX_CSV),
        kospi_closes=_load_closes_csv(ROOT / "research/market_data/kospi_daily_external_yf.csv"),
        weather_gt=_merge_weather_gt(),
    )


def predict_slot(slot_id: str, session_date: str, ctx: BoardContext | None = None) -> dict[str, Any]:
    ctx = ctx or load_context()
    cfg = _slot_cfg(slot_id)
    issued = utc_now()
    base: dict[str, Any] = {
        "slot_id": slot_id,
        "session_date": session_date,
        "issued_at_utc": issued,
        "label_ko": cfg.get("label_ko"),
        "cadence": cfg.get("cadence", "daily"),
    }

    if slot_id == "kospi_direction":
        row = next(
            (r for r in (ctx.kospi_cal.get("rows") or []) if str(r.get("session_date")) == session_date),
            None,
        )
        pred = str((row or {}).get("predicted_direction") or "neutral")
        base.update(
            {
                "predicted_direction": pred,
                "probability_0_1": None,
                "source": "kospi_june2026_calendar",
                "meta": {"session_direction_score": (row or {}).get("session_direction_score")},
            }
        )
        return base

    if slot_id == "foreign_flow":
        hist = []
        for dk in sorted(ctx.flow_by_date):
            if dk < session_date:
                v = ctx.flow_by_date[dk].get("foreign_net_buy")
                if v is not None:
                    hist.append(float(v))
        mean5 = sum(hist[-5:]) / len(hist[-5:]) if hist else 0.0
        p = clamp01(0.5 + math.tanh(mean5 / 200000.0) * 0.2 + _macro_bias())
        base.update(
            {
                "probability_0_1": round(p, 4),
                "predicted_binary": p >= 0.5,
                "source": "flow_5d_mean+macro_lens",
                "meta": {"foreign_5d_mean": round(mean5, 2)},
            }
        )
        return base

    if slot_id == "weather_seoul":
        p = clamp01(0.28 + _macro_bias() * 0.5)
        base.update(
            {
                "probability_0_1": round(p, 4),
                "predicted_binary": p >= 0.5,
                "source": "domain_prior_weather+macro",
                "meta": {"weather_gt_available": session_date in ctx.weather_gt},
            }
        )
        return base

    if slot_id == "usdkrw_direction":
        older = sorted(d for d in ctx.fx_closes if d < session_date)
        prior = ctx.fx_closes[older[-1]] if older else None
        k_older = sorted(d for d in ctx.kospi_closes if d < session_date)
        k_prior = ctx.kospi_closes[k_older[-1]] if k_older else None
        bias = _macro_bias()
        if prior and k_prior and len(k_older) >= 2:
            k_ret = (ctx.kospi_closes[k_older[-1]] - ctx.kospi_closes[k_older[-2]]) / ctx.kospi_closes[k_older[-2]]
            bias -= k_ret * 0.3
        pred = _direction_from_return(bias)
        base.update(
            {
                "predicted_direction": pred,
                "probability_0_1": None,
                "source": "macro_lens+kospi_lag",
                "meta": {"macro_bias": round(bias, 4), "fx_prior": prior},
            }
        )
        return base

    if slot_id == "macro_news_shock":
        p, shock_meta = _news_shock_prob()
        meta = {"shock_threshold_pct": cfg.get("shock_abs_return_pct", 2.0)}
        meta.update(shock_meta)
        base.update(
            {
                "probability_0_1": round(p, 4),
                "predicted_binary": p >= 0.5,
                "source": "news_lens+pre_news_shadow",
                "meta": meta,
            }
        )
        return base

    raise ValueError(f"unknown slot_id: {slot_id}")


def score_slot(slot_id: str, session_date: str, prediction: dict[str, Any], ctx: BoardContext | None = None) -> dict[str, Any]:
    ctx = ctx or load_context()
    cfg = _slot_cfg(slot_id)

    if slot_id == "kospi_direction":
        row = next(
            (r for r in (ctx.kospi_eval.get("rows") or []) if str(r.get("session_date")) == session_date),
            None,
        )
        if not row:
            return {"scorable": False, "reason": "no_kospi_eval_row"}
        return {
            "scorable": True,
            "outcome": row.get("outcome"),
            "predicted_direction": row.get("predicted_direction"),
            "actual_direction": row.get("actual_direction"),
            "daily_return_pct": row.get("daily_return_pct"),
            "band_hit": row.get("band_hit"),
        }

    if slot_id == "foreign_flow":
        flow = ctx.flow_by_date.get(session_date)
        if not flow or flow.get("foreign_net_buy") is None:
            return {"scorable": False, "reason": "missing_flow_row"}
        actual = float(flow["foreign_net_buy"]) > 0
        pred_b = bool(prediction.get("predicted_binary"))
        p = float(prediction.get("probability_0_1") or 0.5)
        outcome = "HIT" if pred_b == actual else "FAIL"
        brier = (p - (1.0 if actual else 0.0)) ** 2
        return {
            "scorable": True,
            "outcome": outcome,
            "actual_binary": actual,
            "predicted_binary": pred_b,
            "probability_0_1": p,
            "brier_contribution": round(brier, 6),
            "foreign_net_buy": flow.get("foreign_net_buy"),
        }

    if slot_id == "weather_seoul":
        if session_date not in ctx.weather_gt:
            return {"scorable": False, "reason": "no_weather_ground_truth"}
        actual = ctx.weather_gt[session_date]
        pred_b = bool(prediction.get("predicted_binary"))
        p = float(prediction.get("probability_0_1") or 0.5)
        outcome = "HIT" if pred_b == actual else "FAIL"
        brier = (p - (1.0 if actual else 0.0)) ** 2
        return {
            "scorable": True,
            "outcome": outcome,
            "actual_binary": actual,
            "predicted_binary": pred_b,
            "probability_0_1": p,
            "brier_contribution": round(brier, 6),
        }

    if slot_id == "usdkrw_direction":
        if session_date not in ctx.fx_closes:
            return {"scorable": False, "reason": "missing_fx_close"}
        older = sorted(d for d in ctx.fx_closes if d < session_date)
        if not older:
            return {"scorable": False, "reason": "no_fx_prior"}
        prior = ctx.fx_closes[older[-1]]
        close = ctx.fx_closes[session_date]
        ret = (close - prior) / prior if prior else 0.0
        actual = _direction_from_return(ret)
        pred = str(prediction.get("predicted_direction") or "neutral")
        return {
            "scorable": True,
            "outcome": _outcome(pred, actual),
            "predicted_direction": pred,
            "actual_direction": actual,
            "daily_return_pct": round(ret * 100, 4),
            "prior_close": round(prior, 4),
            "actual_close": round(close, 4),
        }

    if slot_id == "macro_news_shock":
        from scripts.btrack_macro_news_shock_headline_verify_lib_v1 import (
            headline_gt_for_session,
            load_merged_pre_news_doc,
        )

        if session_date not in ctx.kospi_closes:
            return {"scorable": False, "reason": "missing_kospi_for_shock_proxy"}
        older = sorted(d for d in ctx.kospi_closes if d < session_date)
        if not older:
            return {"scorable": False, "reason": "no_kospi_prior"}
        prior = ctx.kospi_closes[older[-1]]
        close = ctx.kospi_closes[session_date]
        ret_pct = abs((close - prior) / prior * 100.0) if prior else 0.0
        thr = float(cfg.get("shock_abs_return_pct") or 2.0)
        actual_proxy = ret_pct >= thr
        pred_b = bool(prediction.get("predicted_binary"))
        p = float(prediction.get("probability_0_1") or 0.5)
        outcome_proxy = "HIT" if pred_b == actual_proxy else "FAIL"
        brier_proxy = (p - (1.0 if actual_proxy else 0.0)) ** 2

        pre_news = load_merged_pre_news_doc()
        headline = headline_gt_for_session(
            pre_news,
            session_date,
            min_macro_hits=int(cfg.get("headline_shock_min_macro_hits") or 1),
            min_bear_hits=int(cfg.get("headline_shock_min_bear_hits") or 1),
            shock_score_threshold=float(cfg.get("headline_shock_score_threshold") or 0.35),
        )

        result: dict[str, Any] = {
            "scorable": True,
            "predicted_binary": pred_b,
            "probability_0_1": p,
            "abs_return_pct": round(ret_pct, 4),
            "shock_threshold_pct": thr,
            "actual_binary_proxy": actual_proxy,
            "outcome_proxy": outcome_proxy,
            "brier_contribution_proxy": round(brier_proxy, 6),
            "verify_mode": "kospi_abs_return_proxy",
            "outcome": outcome_proxy,
            "actual_binary": actual_proxy,
            "brier_contribution": round(brier_proxy, 6),
        }

        if headline.get("headline_scorable"):
            actual_headline = bool(headline.get("actual_binary_headline"))
            outcome_headline = "HIT" if pred_b == actual_headline else "FAIL"
            brier_headline = (p - (1.0 if actual_headline else 0.0)) ** 2
            result.update(
                {
                    "headline_scorable": True,
                    "actual_binary_headline": actual_headline,
                    "outcome_headline": outcome_headline,
                    "brier_contribution_headline": round(brier_headline, 6),
                    "headline_verify": headline,
                    "verify_mode": "headline_nlp",
                    "outcome": outcome_headline,
                    "actual_binary": actual_headline,
                    "brier_contribution": round(brier_headline, 6),
                }
            )
        else:
            result["headline_scorable"] = False
            result["headline_skip_reason"] = headline.get("reason")

        return result

    raise ValueError(f"unknown slot_id: {slot_id}")


def slot_ids() -> list[str]:
    return [str(s.get("slot_id")) for s in (_load_config().get("slots") or []) if s.get("slot_id")]
