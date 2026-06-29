# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts.rq025_timeapn_dwt_stub_v1 import haar_dwt_level1, timeapn_window_features


def test_haar_dwt_level1_length() -> None:
    x = np.arange(8, dtype=float)
    a, d = haar_dwt_level1(x)
    assert a.size == 4
    assert d.size == 4


def test_timeapn_window_features_finite() -> None:
    s = np.sin(np.linspace(0, 3, 20))
    feats = timeapn_window_features(s, window=8)
    assert np.isfinite(feats["dwt_detail_energy"])
    assert np.isfinite(feats["dwt_approx_last"])
