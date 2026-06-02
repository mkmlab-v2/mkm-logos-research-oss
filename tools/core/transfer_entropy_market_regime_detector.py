# -*- coding: utf-8 -*-
"""B-track Transfer Entropy market regime probe (offline-safe, research_only).

``btrack_probe_v1`` is a lightweight lag-direction predictability proxy on return
series — not a full TE estimator. Used by daily hypothesis chain dumps and
``unified_trading_monitor`` optional path. Does not gate Track A or live orders.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Sequence

import numpy as np

__all__ = [
    "TransferEntropyMarketRegimeDetector",
    "compute_transfer_entropy_probe",
]

_IMPLEMENTATION = "btrack_probe_v1"


def _as_float_array(values: Sequence[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float).flatten()
    return arr[np.isfinite(arr)]


def compute_transfer_entropy_probe(
    returns: Sequence[float] | np.ndarray,
    _news_or_context: Any | None,
    *,
    lookback: int = 20,
) -> float:
    """Lag-1 directional predictability proxy scaled to [0, 5]."""
    arr = _as_float_array(returns)
    if arr.size < 3:
        return 0.0
    window = arr[-max(int(lookback), 3) :]
    signs = np.sign(window)
    signs[signs == 0.0] = 1.0
    lag = signs[:-1]
    cur = signs[1:]
    agree = float(np.mean(lag == cur))
    directional = abs(agree - 0.5) * 2.0
    vol = float(np.std(window))
    vol_base = float(np.mean(np.abs(window))) + 1e-9
    vol_scale = min(2.0, vol / vol_base)
    te = directional * (1.0 + vol_scale) * 2.5
    return float(np.clip(te, 0.0, 5.0))


def _regime_type_from_te(te: float) -> str:
    if te < 1.0:
        return "LOW_TE"
    if te < 2.0:
        return "MODERATE_TE"
    if te < 3.0:
        return "ELEVATED_TE"
    return "HIGH_TE"


def _alert_level_from_te(te: float) -> dict[str, str]:
    if te >= 3.0:
        return {"level": "ELEVATED", "reason": "te_probe_above_3.0"}
    if te >= 2.0:
        return {"level": "WATCH", "reason": "te_probe_above_2.0"}
    return {"level": "NORMAL", "reason": "within_probe_bands"}


class TransferEntropyMarketRegimeDetector:
    """Async-compatible offline TE probe for B-track monitor dumps."""

    def __init__(self, lookback: int = 20) -> None:
        self.lookback = max(int(lookback), 3)

    async def detect_market_regime(
        self,
        returns: Sequence[float] | np.ndarray,
        _noise_series: Sequence[float] | np.ndarray,
        news_texts: Iterable[str] | None,
        current_date: datetime,
    ) -> dict[str, Any]:
        arr = _as_float_array(returns)
        te = compute_transfer_entropy_probe(arr, None, lookback=self.lookback)
        window = arr[-self.lookback :] if arr.size else arr
        sigma_dev = 0.0
        if window.size >= 2:
            sigma_dev = float(np.std(window) / (np.mean(np.abs(window)) + 1e-9))
        news_list = list(news_texts or [])
        return {
            "transfer_entropy": te,
            "sigma_deviation": sigma_dev,
            "regime": {"regime_type": _regime_type_from_te(te)},
            "compression_analysis": None,
            "alert_level": _alert_level_from_te(te),
            "implementation": _IMPLEMENTATION,
            "probe_meta": {
                "lookback": self.lookback,
                "news_texts_n": len(news_list),
                "current_date": current_date.isoformat(),
                "sp500_level": None,
            },
        }
