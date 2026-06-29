# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.rq025_cmdmamba_stub_v1 import cmdmamba_window_features, expand_cmdmamba_series_features


def test_cmdmamba_window_features_finite() -> None:
    s = np.cumsum(np.random.default_rng(0).normal(size=20))
    feats = cmdmamba_window_features(s, window=8)
    for v in feats.values():
        assert np.isfinite(v)


def test_expand_cmdmamba_series_features_keys() -> None:
    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    vbd = {"2026-01-01": 1.0, "2026-01-02": 1.2, "2026-01-03": 0.9}
    out = expand_cmdmamba_series_features(dates, vbd, window=3, prefix="mb_S")
    assert "mb_S_ema_cross" in out["2026-01-03"]
