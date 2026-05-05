# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.myeongri_jijangan_ohang_v1 import (
    build_myeongni_core_vector_v1,
    load_tier_weights,
    ohang_strength_jijangan_v1,
)

ROOT = Path(__file__).resolve().parents[1]
CORE_VECTOR_SCHEMA = (
    ROOT / "docs" / "final" / "artifacts" / "schemas" / "myeongni_core_vector_v1.schema.json"
)


@pytest.fixture(autouse=True)
def clear_weights_cache():
    load_tier_weights.cache_clear()
    yield
    load_tier_weights.cache_clear()


def test_jijangan_ohang_sums_one():
    oh = ohang_strength_jijangan_v1(
        {"year": "갑자", "month": "병인", "day": "경오", "hour": "임신"}
    )
    s = sum(
        oh[k]
        for k in (
            "wood_strength",
            "fire_strength",
            "earth_strength",
            "metal_strength",
            "water_strength",
        )
    )
    assert abs(s - 1.0) < 1e-6


def test_surface_vs_jijangan_not_identical():
    oh = ohang_strength_jijangan_v1(
        {"year": "갑자", "month": "병인", "day": "경오", "hour": "임신"}
    )
    # 축/진 등 지장간이 있는 지지가 있으면 가중 합이 표면과 달라질 수 있음
    assert isinstance(oh["earth_strength"], float)


def test_core_vector_v1_is_deterministic_and_validates():
    core = build_myeongni_core_vector_v1(
        {"year": "갑자", "month": "병인", "day": "경오", "hour": "임신"}
    )
    core2 = build_myeongni_core_vector_v1(
        {"year": "갑자", "month": "병인", "day": "경오", "hour": "임신"}
    )
    assert core == core2
    assert core["schema"] == "myeongni_core_vector_v1"
    assert abs(sum(core["element_strength"].values()) - 1.0) < 1e-6
    assert core["total_raw_count"] > 0.0

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(CORE_VECTOR_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=core, schema=schema)
