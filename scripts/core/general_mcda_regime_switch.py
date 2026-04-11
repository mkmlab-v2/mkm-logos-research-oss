"""Minimal MCDA / regime helpers for general-compression A/B metrics.

Full multi-criteria regime fusion may evolve here; today this module only
supplies stable defaults so ``run_general_compression_ab.py`` can run and
emit ``regime_switch_metrics`` without failing on import.
"""
from __future__ import annotations

from typing import Any


def estimate_signals_from_text(raw: str) -> tuple[float, float]:
    """Return (volatility_proxy, news_shock_proxy). Placeholder: neutral."""
    _ = raw
    return 0.0, 0.0


def derive_vector_4d(
    *,
    volatility: float,
    news_shock_score: float,
    saving_rate: float,
    fidelity: float,
) -> tuple[float, float, float, float]:
    return (float(volatility), float(news_shock_score), float(saving_rate), float(fidelity))


def choose_regime(volatility: float, news_shock: float) -> str:
    _ = volatility, news_shock
    return "normal"


def weighted_risk_score(v4: tuple[float, float, float, float], regime: str) -> float:
    _ = regime
    w, x, y, z = v4
    return float((w + x + y + z) / 4.0)
