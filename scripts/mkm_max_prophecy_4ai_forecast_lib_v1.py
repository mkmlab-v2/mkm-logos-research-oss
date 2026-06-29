#!/usr/bin/env python3
"""MKM 4AI + Absolute Balance Coordinator — Layer-1 forecast fusion for general_prophecy [HYPO].

Reads optional B-track artifacts (macro/news lenses, myeongni/logos/sasang v2, OHLCV score).
Produces deterministic probability_0_1 per question; optional Gemini refine is handled by caller.

NON_GATING: logos/sasang legs capped; no Track A bridge.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DOMAIN_PRIORS: dict[str, float] = {
    "fx": 0.48,
    "equities": 0.50,
    "macro": 0.42,
    "rates": 0.45,
    "commodities": 0.44,
    "crypto": 0.50,
    "geopolitics": 0.35,
    "news_calendar": 0.30,
    "sector": 0.50,
    "weather": 0.28,
    "flows": 0.46,
    "inflation": 0.40,
    "energy": 0.38,
    "trade": 0.34,
    "international": 0.41,
    "korea": 0.48,
    "us": 0.47,
    "europe": 0.45,
    "japan": 0.49,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clamp01(x: float) -> float:
    return max(0.05, min(0.95, float(x)))


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _score_direction_bias(doc: dict[str, Any] | None) -> float:
    """Map latest OHLCV score tail to signed bias in [-0.12, 0.12]."""
    if not doc:
        return 0.0
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict)]
    if not rows:
        return 0.0
    last = rows[-1]
    pred = str(last.get("predicted_direction") or "neutral").lower()
    conf = float(last.get("confidence") or 0.5)
    mag = 0.08 * min(1.0, conf)
    if pred == "bull":
        return mag
    if pred == "bear":
        return -mag
    return 0.0


def _lens_scores_bias(doc: dict[str, Any] | None) -> float:
    if not doc:
        return 0.0
    scores = doc.get("scores")
    if not isinstance(scores, dict):
        return 0.0
    bull = float(scores.get("bull") or scores.get("risk_on") or 0.0)
    bear = float(scores.get("bear") or scores.get("risk_off") or 0.0)
    if bull == 0.0 and bear == 0.0:
        direction = str(scores.get("direction") or "").lower()
        if direction in ("bull", "risk_on", "up"):
            return 0.06
        if direction in ("bear", "risk_off", "down"):
            return -0.06
        return 0.0
    total = bull + bear
    if total <= 0:
        return 0.0
    return clamp01(0.5 + 0.12 * ((bull - bear) / total)) - 0.5


def _response_v2_bias(doc: dict[str, Any] | None, *, cap: float = 0.06) -> float:
    if not doc:
        return 0.0
    decision = str(doc.get("decision") or doc.get("posture") or "").lower()
    conf = float(doc.get("confidence") or doc.get("confidence_0_1") or 0.5)
    mag = cap * min(1.0, conf)
    if decision in ("reduce", "bear", "caution", "hold", "watch"):
        return -mag if decision in ("reduce", "bear", "caution") else -mag * 0.4
    if decision in ("go", "bull", "expand", "active"):
        return mag
    return 0.0


@dataclass
class SignalContext:
    generated_at_utc: str = field(default_factory=utc_now)
    macro_bias: float = 0.0
    news_bias: float = 0.0
    myeongni_bias: float = 0.0
    logos_bias: float = 0.0
    sasang_bias: float = 0.0
    ohlcv_bias: float = 0.0
    sources_present: list[str] = field(default_factory=list)


def load_signal_context(root: Path = ROOT) -> SignalContext:
    ctx = SignalContext()
    paths = {
        "macro_lens": root / "docs/final/artifacts/macro_independent_lens_latest.json",
        "news_lens": root / "docs/final/artifacts/news_independent_lens_latest.json",
        "myeongni_v2": root / "docs/final/artifacts/mkm_myeongni_response_v2_latest.json",
        "logos_v2": root / "docs/final/artifacts/mkm_logos_response_v2_latest.json",
        "sasang": root / "docs/final/artifacts/sasang_independent_lens_latest.json",
        "ohlcv_score": root / "docs/final/artifacts/btrack_prophecy_score_latest.json",
    }
    macro = read_json(paths["macro_lens"])
    news = read_json(paths["news_lens"])
    myeongni = read_json(paths["myeongni_v2"])
    logos = read_json(paths["logos_v2"])
    sasang = read_json(paths["sasang"])
    ohlcv = read_json(paths["ohlcv_score"])

    if macro:
        ctx.sources_present.append("macro_lens")
        ctx.macro_bias = _lens_scores_bias(macro)
    if news:
        ctx.sources_present.append("news_lens")
        ctx.news_bias = _lens_scores_bias(news)
    if myeongni:
        ctx.sources_present.append("myeongni_v2")
        ctx.myeongni_bias = _response_v2_bias(myeongni, cap=0.07)
    if logos:
        ctx.sources_present.append("logos_v2")
        ctx.logos_bias = _response_v2_bias(logos, cap=0.04)
    if sasang:
        ctx.sources_present.append("sasang_lens")
        ctx.sasang_bias = _lens_scores_bias(sasang)
    if ohlcv:
        ctx.sources_present.append("ohlcv_score")
        ctx.ohlcv_bias = _score_direction_bias(ohlcv)
    return ctx


def domain_prior(tags: list[str], prophecy_track: str) -> float:
    for tag in tags:
        if tag in DOMAIN_PRIORS:
            return DOMAIN_PRIORS[tag]
    if prophecy_track == "financial":
        return 0.50
    return 0.42


def _domain_weights(tags: list[str]) -> dict[str, float]:
    tagset = set(tags)
    financialish = bool(tagset & {"fx", "equities", "rates", "commodities", "crypto", "sector", "flows"})
    if financialish:
        return {
            "taeyang": 0.32,
            "taeum": 0.18,
            "soyang": 0.22,
            "soeum": 0.08,
            "ohlcv": 0.12,
            "news": 0.08,
        }
    return {
        "taeyang": 0.38,
        "taeum": 0.14,
        "soyang": 0.14,
        "soeum": 0.12,
        "ohlcv": 0.10,
        "news": 0.12,
    }


def _id_jitter(question_id: str) -> float:
    h = hashlib.sha256(question_id.encode("utf-8")).hexdigest()
    n = int(h[:8], 16) / 0xFFFFFFFF
    return (n - 0.5) * 0.04


def fuse_4ai_probability(
    question: dict[str, Any],
    ctx: SignalContext,
) -> dict[str, Any]:
    tags = [t for t in (question.get("domain_tags") or []) if isinstance(t, str)]
    tagset = set(tags)
    track = str(question.get("prophecy_track") or "general")
    prior = domain_prior(tags, track)
    w = _domain_weights(list(tagset))

    taeyang_p = clamp01(prior + ctx.macro_bias)
    taeum_p = clamp01(prior + ctx.myeongni_bias)
    soyang_p = clamp01(prior + ctx.sasang_bias)
    soeum_p = clamp01(prior + ctx.logos_bias)
    news_p = clamp01(prior + ctx.news_bias)
    ohlcv_p = clamp01(prior + ctx.ohlcv_bias)

    fused = (
        w["taeyang"] * taeyang_p
        + w["taeum"] * taeum_p
        + w["soyang"] * soyang_p
        + w["soeum"] * soeum_p
        + w["news"] * news_p
        + w["ohlcv"] * ohlcv_p
    )
    qid = str(question.get("question_id") or "")
    fused = clamp01(fused + _id_jitter(qid))

    return {
        "probability_0_1": round(fused, 4),
        "coordinator_mode": "absolute_balance_v1",
        "legs": {
            "taeyang_macro": round(taeyang_p, 4),
            "taeum_myeongni": round(taeum_p, 4),
            "soyang_sasang": round(soyang_p, 4),
            "soeum_logos_non_gating": round(soeum_p, 4),
            "news_macro_blend": round(news_p, 4),
            "field_ohlcv": round(ohlcv_p, 4),
        },
        "weights": w,
        "domain_prior": round(prior, 4),
        "signal_sources": list(ctx.sources_present),
    }


def forecast_snapshots(
    *,
    probability: float,
    source_detail: str,
    issued_at: str | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "issued_at_utc": issued_at or utc_now(),
            "probability_0_1": round(clamp01(probability), 4),
            "source_kind": "hybrid",
            "source_detail": source_detail,
            "brier_ready": True,
        }
    ]
