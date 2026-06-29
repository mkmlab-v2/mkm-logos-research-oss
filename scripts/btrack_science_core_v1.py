"""Science Core lane v1 — quant-only price/macro/news fusion [HYPO][research_only].

Excludes sasang/myeongni/logos from score construction. Not a coordinator replacement.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ENSEMBLE_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_MACRO_LENS = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"
DEFAULT_NEWS_LENS = ROOT / "docs/final/artifacts/news_independent_lens_latest.json"
DEFAULT_EXA_NEWS_JSONL = ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl"
MACRO_RISK_LOG = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_v1.jsonl"
MACRO_RISK_BACKFILL_LOG = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_research_backfill_v1.jsonl"

SCIENCE_WEIGHTS_DEFAULT: dict[str, float] = {
    "price": 0.65,
    "macro": 0.20,
    "news": 0.15,
}

BULL = frozenset(
    "rally surge gain up bull recovery expansion stabilize stabilization growth rebound "
    "support risk-on riskon breakthrough momentum".split()
)
BEAR = frozenset(
    "crisis crash down bear selloff fear tighten tightening slump recession loss "
    "risk-off riskoff stress shock decline plunge".split()
)

TIE_BREAK_MARGIN = 0.03
DIRECTION_THRESHOLD = 0.08


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def score_texts_keyword_tilt(texts: list[str]) -> tuple[float, float, dict[str, Any]]:
    if not texts:
        return 0.0, 0.0, {"reason": "no_text", "n": 0}
    raw = 0.0
    for t in texts:
        tok = _tokenize(t)
        raw += sum(1.0 for w in BULL if w in tok)
        raw -= sum(1.0 for w in BEAR if w in tok)
    n = len(texts)
    direction = max(-1.0, min(1.0, raw / max(1.0, 2.0 * n)))
    confidence = min(1.0, 0.12 + 0.06 * min(n, 8))
    return direction, confidence, {"n_texts": n, "raw_tilt": raw}


def load_science_weights(cfg_path: Path | None = None) -> dict[str, float]:
    """Renormalize price/macro/news from ensemble config; humanist keys excluded."""
    path = cfg_path or DEFAULT_ENSEMBLE_CFG
    doc = _read_json(path) or {}
    raw = doc.get("weights") if isinstance(doc.get("weights"), dict) else {}
    picked = {
        "price": _safe_float(raw.get("price"), SCIENCE_WEIGHTS_DEFAULT["price"]),
        "macro": _safe_float(raw.get("macro"), SCIENCE_WEIGHTS_DEFAULT["macro"]),
        "news": _safe_float(raw.get("news"), SCIENCE_WEIGHTS_DEFAULT["news"]),
    }
    total = sum(abs(v) for v in picked.values())
    if total <= 1e-12:
        return dict(SCIENCE_WEIGHTS_DEFAULT)
    return {k: v / total for k, v in picked.items()}


def price_lens_from_returns(returns: list[float], *, lookback_rows: int) -> tuple[float, float, dict[str, Any]]:
    if not returns:
        return 0.0, 0.0, {"reason": "no_returns", "lookback_rows": lookback_rows}
    avg_ret = sum(returns) / len(returns)
    abs_returns = [abs(v) for v in returns]
    abs_ret_mean = sum(abs_returns) / len(abs_returns)
    direction_score = max(-1.0, min(1.0, avg_ret / 0.02))
    confidence = max(0.0, min(1.0, abs(direction_score)))
    return direction_score, confidence, {
        "lookback_rows": lookback_rows,
        "avg_daily_return": round(avg_ret, 8),
        "recent_abs_return_mean": round(abs_ret_mean, 8),
        "mode": "causal_ohlcv_momentum",
    }


def build_daily_returns(closes: dict[str, float], trading_days: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for i in range(1, len(trading_days)):
        d_prev, d_cur = trading_days[i - 1], trading_days[i]
        c0, c1 = closes.get(d_prev), closes.get(d_cur)
        if c0 is None or c1 is None or c0 == 0:
            continue
        out[d_cur] = (c1 - c0) / c0
    return out


def price_lens_causal_at_index(
    daily_returns: dict[str, float],
    trading_days: list[str],
    idx: int,
    *,
    lookback: int = 5,
) -> tuple[float, float, dict[str, Any]]:
    if idx < 1:
        return 0.0, 0.0, {"reason": "insufficient_history", "lookback": lookback}
    ed = trading_days[idx]
    prior_days = [d for d in trading_days[: idx + 1] if d in daily_returns]
    tail_days = prior_days[-max(1, lookback) :]
    tail = [daily_returns[d] for d in tail_days]
    score, conf, meta = price_lens_from_returns(tail, lookback_rows=len(tail))
    meta["eval_date"] = ed
    meta["causal_through"] = ed
    return score, conf, meta


def _row_day(row: dict[str, Any]) -> str | None:
    for key in (
        "session_date",
        "eval_date",
        "calendar_date",
        "logged_at_utc",
        "published_utc",
        "as_of_utc",
        "ts_utc",
    ):
        ts = str(row.get(key) or "")
        if len(ts) >= 10 and ts[4] == "-":
            return ts[:10]
    return None


def _decision_to_direction(decision_state: str | None, risk_level: str | None = None) -> str:
    s = str(decision_state or "").strip().upper()
    lvl = str(risk_level or "").strip().lower()
    if s in {"GO", "RISK_ON"}:
        return "bull"
    if s in {"REDUCE", "NO_GO", "HOLD", "LOCKED"}:
        return "bear"
    if s in {"CALM", "NEUTRAL", "NEUTRAL_BAND"}:
        return "neutral"
    if s == "WATCH" or lvl in {"elevated", "high", "critical"}:
        return "bear"
    return "neutral"


def _direction_to_score(direction: str) -> float:
    d = direction.strip().lower()
    if d == "bull":
        return 0.55
    if d == "bear":
        return -0.55
    return 0.0


def build_macro_gate_by_day(gate_paths: list[tuple[int, Path]] | None = None) -> dict[str, dict[str, Any]]:
    from scripts.run_three_lens_horizon_empirical_eval_v2 import _build_gate_by_day_tiered

    sources = gate_paths or [
        (2, MACRO_RISK_BACKFILL_LOG),
        (1, MACRO_RISK_LOG),
    ]
    return _build_gate_by_day_tiered(sources)


def macro_lens_at_date(
    gate_by_day: dict[str, dict[str, Any]],
    eval_date: str,
    *,
    global_macro_path: Path | None = None,
    trailing_dir: str | None = None,
) -> tuple[float, float, dict[str, Any]]:
    from scripts.run_three_lens_horizon_empirical_eval_v2 import _gate_asof

    ed = eval_date[:10]
    gate_row = _gate_asof(gate_by_day, ed)
    if gate_row:
        direction = _decision_to_direction(
            str(gate_row.get("decision_state") or ""),
            str(gate_row.get("risk_warning_level") or ""),
        )
        score = _direction_to_score(direction)
        return score, 0.55, {
            "mode": "causal_macro_risk_gate_asof",
            "direction": direction,
            "gate_schema": gate_row.get("schema"),
        }

    if trailing_dir:
        score = _direction_to_score(trailing_dir)
        return score, 0.35, {
            "mode": "trailing_21d_ohlcv_fallback",
            "direction": trailing_dir,
        }

    path = global_macro_path or DEFAULT_MACRO_LENS
    doc = _read_json(path) or {}
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    score = _safe_float(scores.get("direction_score"), 0.0)
    conf = _safe_float(scores.get("confidence"), 0.3)
    return score, conf, {"mode": "global_macro_snapshot", "direction": direction_from_score(score)}


def build_news_by_published_day(jsonl_path: Path | None = None) -> dict[str, list[str]]:
    path = jsonl_path or DEFAULT_EXA_NEWS_JSONL
    by_day: dict[str, list[str]] = {}
    for row in _read_jsonl(path):
        day = _row_day(row)
        if not day:
            continue
        text = str(row.get("canonical_text") or row.get("text") or "").strip()
        if text:
            by_day.setdefault(day, []).append(text)
    return by_day


def news_lens_at_date(
    news_by_day: dict[str, list[str]],
    eval_date: str,
    *,
    lookback_calendar_days: int = 14,
    global_news_path: Path | None = None,
) -> tuple[float, float, dict[str, Any]]:
    ed = eval_date[:10]
    texts: list[str] = []
    eligible_days = sorted(d for d in news_by_day if d <= ed)
    if eligible_days:
        window = eligible_days[-lookback_calendar_days:]
        for d in window:
            texts.extend(news_by_day.get(d, []))
    if texts:
        score, conf, meta = score_texts_keyword_tilt(texts)
        meta["mode"] = "causal_exa_news_window"
        meta["window_days"] = len(window)
        meta["eval_date"] = ed
        return score, conf, meta

    path = global_news_path or DEFAULT_NEWS_LENS
    doc = _read_json(path) or {}
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    score = _safe_float(scores.get("direction_score"), 0.0)
    conf = _safe_float(scores.get("confidence"), 0.25)
    return score, conf, {"mode": "global_news_snapshot", "eval_date": ed}


def recompose_science_from_components(
    row: dict[str, Any],
    weights: dict[str, float],
) -> tuple[float, str]:
    """Re-blend stored price/macro/news component scores with alternate weights."""
    comps = row.get("components") if isinstance(row.get("components"), dict) else {}
    keys = ("price", "macro", "news")
    w_raw = {k: max(0.0, _safe_float(weights.get(k), 0.0)) for k in keys}
    w_sum = sum(w_raw.values())
    if w_sum <= 0:
        return 0.0, "neutral"
    w_norm = {k: w_raw[k] / w_sum for k in keys}
    weighted = sum(
        w_norm[k] * _safe_float((comps.get(k) or {}).get("direction_score"), 0.0) for k in keys
    )
    return weighted, direction_from_score(weighted)


def direction_from_score(score: float, *, margin: float = TIE_BREAK_MARGIN) -> str:
    if abs(score) < margin:
        return "neutral"
    if score > DIRECTION_THRESHOLD:
        return "bull"
    if score < -DIRECTION_THRESHOLD:
        return "bear"
    if score > 0:
        return "bull"
    if score < 0:
        return "bear"
    return "neutral"


def compose_science_core(
    *,
    price_score: float,
    price_conf: float,
    price_meta: dict[str, Any],
    macro_score: float,
    macro_conf: float,
    macro_meta: dict[str, Any],
    news_score: float,
    news_conf: float,
    news_meta: dict[str, Any],
    weights: dict[str, float] | None = None,
    instrument: str = "kospi",
    session_date: str = "",
    apply_overnight: bool = False,
) -> dict[str, Any]:
    w = weights or load_science_weights()
    p_score, p_conf, p_meta = price_score, price_conf, dict(price_meta)
    if apply_overnight and instrument == "kospi":
        from scripts.kospi_overnight_price_overlay_v1 import apply_kospi_overnight_price_overlay

        p_score, p_conf, p_meta = apply_kospi_overnight_price_overlay(p_score, p_conf, p_meta)

    components = {
        "price": {"direction_score": round(p_score, 6), "confidence": round(p_conf, 6), **p_meta},
        "macro": {"direction_score": round(macro_score, 6), "confidence": round(macro_conf, 6), **macro_meta},
        "news": {"direction_score": round(news_score, 6), "confidence": round(news_conf, 6), **news_meta},
    }

    weighted = sum(_safe_float(w.get(k), 0.0) * _safe_float(components[k]["direction_score"]) for k in components)
    conf_vals = [
        _safe_float(w.get(k), 0.0) * _safe_float(components[k]["confidence"]) for k in components
    ]
    w_sum = sum(_safe_float(w.get(k), 0.0) for k in components) or 1.0
    confidence = sum(conf_vals) / w_sum

    direction = direction_from_score(weighted)
    return {
        "schema": "btrack_science_core_per_date_v1",
        "session_date": session_date[:10],
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "lane_id": "science_core_v1",
        "instrument": instrument,
        "excludes_humanist_lenses": True,
        "weights": {k: round(_safe_float(w.get(k)), 6) for k in components},
        "components": components,
        "scores": {
            "direction_score": round(weighted, 6),
            "confidence": round(confidence, 6),
        },
        "direction": direction,
        "note": "Quant-only lane; not coordinator mode; not Track A promotion.",
    }


def combo_direction_from_scores(
    science_score: float,
    humanist_score: float,
    *,
    science_weight: float = 0.5,
    humanist_weight: float = 0.5,
) -> str:
    total_w = science_weight + humanist_weight
    if total_w <= 0:
        return direction_from_score(science_score)
    blended = (science_weight * science_score + humanist_weight * humanist_score) / total_w
    return direction_from_score(blended)


TRIPLE_BLEND_WEIGHTS: dict[str, float] = {"science": 0.50, "sasang": 0.25, "myeongni": 0.25}


def triple_sasang_myeongni_direction(
    science_score: float,
    sasang_score: float,
    myeongni_score: float,
) -> str:
    w = TRIPLE_BLEND_WEIGHTS
    blended = (
        w["science"] * science_score
        + w["sasang"] * sasang_score
        + w["myeongni"] * myeongni_score
    )
    return direction_from_score(blended)
