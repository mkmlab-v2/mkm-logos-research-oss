# -*- coding: utf-8 -*-
"""Unit tests: deterministic gematria–myeongri 4D math (no subprocess, no I/O)."""

from __future__ import annotations

import math

from tools.myeongni.gematria_myeongri_math_v1 import (
    MATH_MODULE_ID,
    MATH_MODULE_VERSION,
    blend_convex_renorm,
    coerce_4d,
    cosine_similarity,
    geometric_metrics,
    l2_distance,
    renorm_4d,
)


def test_renorm_uniform_when_zero_sum() -> None:
    z = {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0}
    out = renorm_4d(z)
    assert out == {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}


def test_blend_convex_renorm_midpoint_on_simplex() -> None:
    a = {"S": 1.0, "L": 0.0, "K": 0.0, "M": 0.0}
    b = {"S": 0.0, "L": 1.0, "K": 0.0, "M": 0.0}
    h = blend_convex_renorm(a, b, 0.5)
    assert abs(h["S"] - 0.5) < 1e-9
    assert abs(h["L"] - 0.5) < 1e-9
    assert h["K"] == 0.0 and h["M"] == 0.0
    s = sum(h.values())
    assert abs(s - 1.0) < 1e-9


def test_l2_cosine_orthogonal() -> None:
    a = {"S": 1.0, "L": 0.0, "K": 0.0, "M": 0.0}
    b = {"S": 0.0, "L": 1.0, "K": 0.0, "M": 0.0}
    assert abs(l2_distance(a, b) - math.sqrt(2)) < 1e-9
    assert abs(cosine_similarity(a, b) - 0.0) < 1e-9


def test_geometric_metrics_keys() -> None:
    v = {"S": 0.4, "L": 0.3, "K": 0.2, "M": 0.1}
    m = {"S": 0.1, "L": 0.2, "K": 0.3, "M": 0.4}
    h = blend_convex_renorm(v, m, 0.25)
    g = geometric_metrics(v, m, h)
    assert set(g) == {
        "l2_vanilla_myeongri",
        "l2_vanilla_hybrid",
        "cosine_vanilla_myeongri",
        "cosine_vanilla_hybrid",
    }


def test_module_identity() -> None:
    assert MATH_MODULE_ID == "gematria_myeongri_math_v1"
    assert MATH_MODULE_VERSION == "1.0.0"


def test_coerce_4d_defaults_missing() -> None:
    assert coerce_4d({"S": 2.0}) == {"S": 2.0, "L": 0.0, "K": 0.0, "M": 0.0}
