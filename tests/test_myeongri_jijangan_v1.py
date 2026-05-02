# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
LUT_PATH = _ROOT / "data" / "myeongni" / "jijangan_lut_v1.json"
_MOD_PATH = _ROOT / "scripts" / "myeongri_jijangan_v1.py"


def _load_mod():
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    spec = importlib.util.spec_from_file_location("myeongri_jijangan_v1", _MOD_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lut_loads_and_covers_twelve_branches():
    mod = _load_mod()
    mod.load_lut.cache_clear()
    doc = mod.load_lut()
    assert doc["version"]
    assert set(doc["branches"].keys()) == mod.JIJI
    mod.validate_against_schema_file(doc)
    raw = json.loads(LUT_PATH.read_text(encoding="utf-8"))
    mod.validate_against_schema_file(raw)


@pytest.mark.parametrize(
    "ji,first_gan",
    [
        ("자", "계"),
        ("묘", "을"),
        ("인", "갑"),
        ("오", "정"),
        ("해", "임"),
    ],
)
def test_sample_jijangan_order(ji, first_gan):
    mod = _load_mod()
    mod.load_lut.cache_clear()
    rows = mod.hidden_stems_for_branch(ji)
    assert rows[0]["gan"] == first_gan
    assert rows[0]["tier"] == "jeong_gi"
    assert mod.all_gans_for_branch(ji)[0] == first_gan


def test_unknown_branch_raises():
    mod = _load_mod()
    mod.load_lut.cache_clear()
    with pytest.raises(KeyError):
        mod.hidden_stems_for_branch("X")


def test_overlay_matches_four_pillars():
    mod = _load_mod()
    mod.load_lut.cache_clear()
    out = mod.jijangan_overlay_for_saju(
        {"year": "갑자", "month": "병인", "day": "경오", "hour": "임신"}
    )
    assert out["lut_version"]
    assert out["pillars"]["year"]["ji"] == "자"
    assert out["pillars"]["year"]["hidden_stems"][0]["gan"] == "계"
    assert out["pillars"]["month"]["ji"] == "인"
    assert out["pillars"]["month"]["hidden_stems"][0]["gan"] == "갑"


def test_overlay_tolerates_bad_pillar():
    mod = _load_mod()
    mod.load_lut.cache_clear()
    out = mod.jijangan_overlay_for_saju({"year": "갑", "month": "", "day": "XX", "hour": "임시"})
    assert out["pillars"]["year"]["note"] == "short_or_empty_pillar"
    assert out["pillars"]["month"]["hidden_stems"] == []
    assert out["pillars"]["day"]["note"] == "ji_not_in_lut_alphabet"
