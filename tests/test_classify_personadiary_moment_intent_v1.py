"""PersonaDiary moment intent classifier v1."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from classify_personadiary_moment_intent_v1 import classify_intent  # noqa: E402


def test_meal_intent() -> None:
    out = classify_intent("오늘 점심 뭐 먹을까?")
    assert out["intent"] == "meal"
    assert out["score"] >= 1


def test_weather_fit_intent() -> None:
    out = classify_intent("오늘 날씨에 뭐 입을까")
    assert out["intent"] == "weather_fit"


def test_mood_intent() -> None:
    out = classify_intent("요즘 기분이 가라앉아")
    assert out["intent"] == "mood"


def test_world_me_intent() -> None:
    out = classify_intent("오늘 뉴스 보니 불안해")
    assert out["intent"] == "world_me"


def test_reflect_fallback() -> None:
    out = classify_intent("그냥 생각 정리하고 싶어")
    assert out["intent"] == "reflect"
    assert out["hypothesis_tier"] == "B"
