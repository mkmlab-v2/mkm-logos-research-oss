# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCR = _ROOT / "scripts" / "btrack_yang_2015_style_metrics_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("btrack_yang_2015_style_metrics_v1", _SCR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["btrack_yang_2015_style_metrics_v1"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_all_gapsja_甲子_counts():
    mod = _load()
    pillars = {"year": "甲子", "month": "甲子", "day": "甲子", "hour": "甲子"}
    m = mod.compute_yang_style_metrics(pillars)
    assert m["element_counts_surface_8"]["wood"] == 4
    assert m["element_counts_surface_8"]["water"] == 4
    assert m["yinyang_counts_surface_8"]["yang"] == 8
    assert m["six_god_buckets_yang2015_names"]["parallel"] == 3
    assert m["six_god_buckets_yang2015_names"]["resource"] == 4


def test_gwaegang_fixture_pillars_have_mixed_buckets():
    mod = _load()
    pillars = {"year": "갑자", "month": "갑자", "day": "경진", "hour": "갑자"}
    m = mod.compute_yang_style_metrics(pillars)
    assert sum(m["six_god_buckets_yang2015_names"].values()) == 7
    assert m["day_stem"] == "경"
