# -*- coding: utf-8 -*-
"""scripts/myeongri_* 보강 모듈 스모크 — import·4D 키·합=1."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_lambda_converter import MyeongriLambdaConverter
from scripts.myeongri_complete_fusion import MyeongriCompleteFusion


def test_lambda_converter_instantiate() -> None:
    c = MyeongriLambdaConverter()
    lam = c.scalar_from_4d({"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25})
    assert isinstance(lam, float)
    assert 0.0 <= lam <= 0.5


def test_complete_fusion_returns_normalized_4d() -> None:
    f = MyeongriCompleteFusion()
    r = f.calculate_complete_fusion(2000, 1, 1, 12, is_solar=True, is_male=True)
    v = r["vector_4d"]
    for k in ("S", "L", "K", "M"):
        assert k in v
    assert abs(sum(v[k] for k in ("S", "L", "K", "M")) - 1.0) < 1e-6
    assert "ohang_strength" in r


def test_myeongri_controller_default_init() -> None:
    from tools.core.myeongri_controller import MyeongriController, MYEONGRI_AVAILABLE

    assert MYEONGRI_AVAILABLE is True
    mc = MyeongriController()
    assert mc.birth_year == 2000
    v = mc._get_base_vector_4d()
    assert abs(sum(v[k] for k in ("S", "L", "K", "M")) - 1.0) < 1e-5
