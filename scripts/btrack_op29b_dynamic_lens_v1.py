"""O-P29b: per-eval_date dynamic lens injection for B-track ensemble (research_only).

- myeongni/sasang: causal calendar JSONL as-of (<= eval_date).
- news: pre_news_shadow rows with timestamp_utc <= eval_date (look-ahead blocked).
- macro: dated news tilt + static macro seeds when no per-day macro feed exists.

Does not mutate docs/final/artifacts/prophecy_hit_rate_eval_latest.json.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
DEFAULT_PRE_NEWS = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"
DEFAULT_MACRO_SIGNALS = ROOT / "docs/final/artifacts/external_macro_signals_latest.json"
DEFAULT_EXTERNAL_NEWS = ROOT / "docs/final/artifacts/external_news_feed_latest.json"

BULL = frozenset(
    "rally surge gain up bull recovery expansion stabilize stabilization growth rebound "
    "support risk-on riskon breakthrough momentum".split()
)
BEAR = frozenset(
    "crisis crash down bear selloff fear tighten tightening slump recession loss "
    "risk-off riskoff stress shock decline plunge".split()
)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def score_from_texts(texts: list[str]) -> tuple[float, float, dict[str, Any]]:
    if not texts:
        return 0.0, 0.18, {"reason": "no_text", "n": 0}
    raw = 0.0
    for t in texts:
        tok = _tokenize(t)
        raw += sum(1.0 for w in BULL if w in tok)
        raw -= sum(1.0 for w in BEAR if w in tok)
    n = len(texts)
    direction = max(-1.0, min(1.0, raw / max(1.0, 2.0 * n)))
    confidence = min(1.0, 0.12 + 0.06 * min(n, 8))
    return direction, confidence, {"n_texts": n, "raw_tilt": raw}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _calendar_day_from_ts(ts: str) -> str | None:
    ts = str(ts or "").strip()
    if len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
        return ts[:10]
    return None


def headlines_asof_pre_news(doc: dict[str, Any] | None, eval_date: str) -> list[str]:
    if not doc:
        return []
    ed = eval_date[:10]
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = _calendar_day_from_ts(str(row.get("timestamp_utc") or row.get("published_utc") or ""))
        if day and day > ed:
            continue
        h = str(row.get("headline") or row.get("title") or "").strip()
        if h:
            out.append(h)
    return out


def macro_seed_texts_global(doc: dict[str, Any] | None) -> list[str]:
    if not doc:
        return []
    seeds: list[str] = []
    mt = doc.get("macro_trend") if isinstance(doc.get("macro_trend"), dict) else {}
    trend = str(mt.get("trend") or "").strip().lower()
    if trend == "up":
        seeds.append("growth expansion recovery")
    elif trend == "down":
        seeds.append("contraction risk-off stress")
    elif trend == "flat":
        seeds.append("stabilization policy support")
    try:
        sc = float(mt.get("score"))
        if sc > 0.05:
            seeds.append("macro positive drift")
        elif sc < -0.05:
            seeds.append("macro negative drift")
    except (TypeError, ValueError):
        pass
    return seeds


def news_macro_scores_for_eval_date(
    eval_date: str,
    *,
    pre_news_path: Path = DEFAULT_PRE_NEWS,
    macro_path: Path = DEFAULT_MACRO_SIGNALS,
    external_news_path: Path = DEFAULT_EXTERNAL_NEWS,
) -> tuple[dict[str, Any], dict[str, Any]]:
    ed = eval_date[:10]
    pre = _load_json(pre_news_path)
    headlines = headlines_asof_pre_news(pre, ed)
    ext = _load_json(external_news_path)
    if ext and isinstance(ext.get("data"), list):
        for it in ext["data"]:
            if not isinstance(it, dict):
                continue
            day = _calendar_day_from_ts(str(it.get("publishedAt") or it.get("published_utc") or it.get("date") or ""))
            if day and day > ed:
                continue
            for k in ("headline", "title", "description", "summary"):
                v = str(it.get(k) or "").strip()
                if v:
                    headlines.append(v)
    n_dir, n_conf, n_meta = score_from_texts(headlines)
    news_block = {
        "direction_score": n_dir,
        "confidence": n_conf,
        "meta": {**n_meta, "adapter": "op29b_news_asof_v1", "eval_date": ed, "headline_count": len(headlines)},
    }

    macro_doc = _load_json(macro_path)
    m_texts = macro_seed_texts_global(macro_doc)
    if headlines:
        m_texts = m_texts + headlines[:2]
    m_dir, m_conf, m_meta = score_from_texts(m_texts)
    macro_block = {
        "direction_score": m_dir,
        "confidence": max(m_conf, 0.25 if m_texts else 0.18),
        "meta": {**m_meta, "adapter": "op29b_macro_hybrid_v1", "eval_date": ed, "note": "macro seeds global + news as-of blend"},
    }
    return news_block, macro_block


def myeongni_sasang_scores_for_eval_date(
    eval_date: str,
    *,
    myeongni_jsonl: Path = DEFAULT_MYEONGNI_JSONL,
    sasang_jsonl: Path = DEFAULT_SASANG_JSONL,
    momentum_window: int = 5,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from scripts.btrack_multilens_per_date_core_v1 import (
        causal_rows_through,
        read_jsonl,
        row_asof,
        rows_by_calendar_day,
        score_myeongni_at_date,
        score_sasang_at_date,
    )

    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    ed = eval_date[:10]
    my_hist = causal_rows_through(my_by, ed)
    my_day, _ = row_asof(my_by, ed)
    sa_day, sa_row = row_asof(sa_by, ed)
    my = score_myeongni_at_date(my_hist, eval_date=ed, matched_day=my_day, momentum_window=momentum_window)
    sa = score_sasang_at_date(sa_row, matched_day=sa_day, eval_date=ed)
    return my, sa


def patch_bundle_for_eval_date(
    bundle: dict[str, Any],
    eval_date: str,
    *,
    pre_news_path: Path = DEFAULT_PRE_NEWS,
    macro_path: Path = DEFAULT_MACRO_SIGNALS,
    external_news_path: Path = DEFAULT_EXTERNAL_NEWS,
    myeongni_jsonl: Path = DEFAULT_MYEONGNI_JSONL,
    sasang_jsonl: Path = DEFAULT_SASANG_JSONL,
) -> dict[str, Any]:
    b = copy.deepcopy(bundle)
    arts = b.setdefault("artifacts", {})
    my, sa = myeongni_sasang_scores_for_eval_date(
        eval_date, myeongni_jsonl=myeongni_jsonl, sasang_jsonl=sasang_jsonl
    )
    news, macro = news_macro_scores_for_eval_date(
        eval_date,
        pre_news_path=pre_news_path,
        macro_path=macro_path,
        external_news_path=external_news_path,
    )

    def _patch_art(key: str, scores: dict[str, Any], stream: str) -> None:
        base = arts.get(key) if isinstance(arts.get(key), dict) else {}
        art = copy.deepcopy(base) if base else {
            "schema": key,
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "research_only": True,
        }
        art["scores"] = {
            "direction_score": float(scores.get("direction_score") or 0.0),
            "confidence": float(scores.get("confidence") or 0.18),
        }
        art["op29b_dynamic_v1"] = {
            "eval_date": eval_date[:10],
            "stream": stream,
            "meta": scores.get("meta") or {},
            "matched_calendar_day": scores.get("matched_calendar_day"),
            "data_quality": scores.get("data_quality"),
        }
        arts[key] = art

    _patch_art("myeongni_independent_lens", my, "myeongni_calendar_jsonl")
    _patch_art("sasang_independent_lens", sa, "sasang_calendar_jsonl")
    _patch_art("news_independent_lens", news, "news_pre_shadow_asof")
    _patch_art("macro_independent_lens", macro, "macro_hybrid_asof")
    return b
