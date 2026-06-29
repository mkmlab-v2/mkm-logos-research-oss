# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.rq025_chronos_stub_v1 import chronos_window_features, expand_chronos_series_features


def test_chronos_window_features_finite() -> None:
    s = np.linspace(1.0, 2.0, 20)
    feats = chronos_window_features(s, window=8)
    for v in feats.values():
        assert np.isfinite(v)


def test_expand_chronos_series_features_keys() -> None:
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    vbd = {"2026-01-01": 1.0, "2026-01-02": 1.1, "2026-01-03": 1.2}
    out = expand_chronos_series_features(dates, vbd, window=3, prefix="ch_K")
    assert "ch_K_residual" in out["2026-01-03"]
    assert np.isfinite(out["2026-01-03"]["ch_K_trend_slope"])
