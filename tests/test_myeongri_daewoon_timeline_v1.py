# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.myeongri_daewoon_timeline_v1 import (
    _active_cycle_index,
    build_myeongri_daewoon_timeline_v1,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "schemas"
    / "myeongri_daewoon_timeline_v1.schema.json"
)


def test_active_cycle_index_boundary_policy():
    rows = [
        {"age_start": 7.0, "age_end": 17.0},
        {"age_start": 17.0, "age_end": 27.0},
    ]
    assert _active_cycle_index(rows, 6.99) is None
    assert _active_cycle_index(rows, 7.0) == 0
    assert _active_cycle_index(rows, 16.9999) == 0
    assert _active_cycle_index(rows, 17.0) == 1
    assert _active_cycle_index(rows, 99.0) == 1


def test_timeline_v1_builds_and_validates_schema():
    timeline = build_myeongri_daewoon_timeline_v1(
        birth_year=1992,
        birth_month=3,
        birth_day=12,
        birth_hour=17,
        month_pillar="기해",
        year_gan="갑",
        is_male=True,
        num_cycles=10,
        as_of_utc="2026-05-05T00:00:00Z",
    )
    assert timeline["schema"] == "myeongri_daewoon_timeline_v1"
    assert timeline["qiyun_meta_v1"]["schema"] == "qiyun_v1"
    assert len(timeline["daewoon_rows"]) == 10
    assert timeline["daewoon_rows"][0]["qiyun_applied"] is True
    active = timeline["active_cycle"]
    assert active is not None
    idx = active["index_zero_based"]
    assert timeline["daewoon_rows"][idx]["cycle"] == active["cycle"]

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=timeline, schema=schema)

