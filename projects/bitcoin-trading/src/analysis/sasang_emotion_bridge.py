# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.88, K:0.55, M:0.78}
# Balance: 90
# Purpose: Map hybrid market emotion signals to memory weight features.
# Keywords: emotion, sasang, panic_ratio, fomo_index, valence, arousal, uncertainty
#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


def _clip(v: float, low: float, high: float) -> float:
    return max(low, min(high, v))


@dataclass(frozen=True)
class EmotionWeight:
    valence: float
    arousal: float
    uncertainty: float
    ae: float
    no: float
    hui: float
    rak: float
    source_mode: str


def build_emotion_weight(
    *,
    panic_ratio: Optional[float] = None,
    fomo_index: Optional[float] = None,
    market_volatility: Optional[float] = None,
    market_sentiment_latent: Optional[float] = None,
    llm_sentiment_score: Optional[float] = None,
) -> EmotionWeight:
    """
    Hybrid mapping:
    - Quant anchors (panic/fomo/volatility) are primary.
    - LLM/text sentiment is secondary and uncertainty only decreases when aligned.
    """
    p = _clip(float(panic_ratio or 0.5), 0.0, 1.0)
    f = _clip(float(fomo_index or 0.5), 0.0, 1.0)
    v = _clip(float(market_volatility or 0.5), 0.0, 1.0)

    q_valence = _clip(f - p, -1.0, 1.0)
    q_arousal = _clip(0.55 * v + 0.25 * p + 0.20 * f, 0.0, 1.0)
    q_uncertainty = _clip(0.60 * v + 0.20 * abs(q_valence) + 0.20 * (1.0 - abs(q_valence)), 0.0, 1.0)

    source_mode = "quant_only"
    txt_signal = market_sentiment_latent if market_sentiment_latent is not None else llm_sentiment_score
    if txt_signal is not None:
        t = _clip(float(txt_signal), -1.0, 1.0)
        valence = _clip(0.70 * q_valence + 0.30 * t, -1.0, 1.0)
        aligned = 1.0 if (q_valence == 0.0 or t == 0.0 or (q_valence * t) > 0) else 0.0
        uncertainty = _clip(q_uncertainty * (0.85 if aligned else 1.10), 0.0, 1.0)
        source_mode = "hybrid_quant_text"
    else:
        valence = q_valence
        uncertainty = q_uncertainty

    arousal = q_arousal

    # Sadness(shrink), Anger(rebound impulse), Joy(relax), Pleasure(overheat)
    ae = _clip(0.65 * p + 0.35 * (1.0 - arousal), 0.0, 1.0)
    no = _clip(0.60 * p + 0.40 * arousal, 0.0, 1.0)
    hui = _clip(0.70 * max(0.0, valence) + 0.30 * (1.0 - v), 0.0, 1.0)
    rak = _clip(0.70 * f + 0.30 * arousal, 0.0, 1.0)

    return EmotionWeight(
        valence=valence,
        arousal=arousal,
        uncertainty=uncertainty,
        ae=ae,
        no=no,
        hui=hui,
        rak=rak,
        source_mode=source_mode,
    )

