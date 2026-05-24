"""Lifestyle concierge rules — no network."""

from __future__ import annotations

import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import commander_lifestyle_concierge_v1 as lc  # noqa: E402


def test_build_lifestyle_payload_rain_taeyang(tmp_path: Path) -> None:
    profile = {
        "schema": "commander_profile_v1",
        "sasang_reference": {"label": "태양인"},
        "myeongni_fact_ref": {
            "element_counts_visible": {"목": 2, "화": 0, "토": 3, "금": 1, "수": 2},
            "day_master_stem": "경",
        },
    }
    report = {
        "day_master": {"stem_hangul": "경"},
        "structure_analysis": {
            "element_profile": {"dominant_element_visible": "토", "weakest_element_visible": "화"},
        },
        "monthly_fortune": {
            "rows": [{"year": 2026, "month": 5, "wolwoon_stem_ten_god": "상관"}]
        },
    }
    weather = {
        "city_label_ko": "서울",
        "current": {
            "band": "rain",
            "summary_ko": "18°C · 비·습기",
            "temperature_c": 18,
        },
    }
    payload = lc.build_lifestyle_payload(profile=profile, report=report, weather=weather)
    assert payload["schema"] == "commander_lifestyle_concierge_v1"
    assert payload["weather_band"] == "rain"
    assert payload["sasang_label"] == "태양인"
    lunch = payload["meals"]["lunch_ko"]
    assert "닭곰탕" in lunch or "국" in lunch
    lines = "\n".join(payload["telegram_append_lines"])
    assert "라이프" in lines
    assert "서울" in lines
    assert "[가설]" in lines or "[HYPO]" in lines


def test_weather_band_rain() -> None:
    assert lc._weather_band(61, 0.5, 15.0) == "rain"
    assert lc._weather_band(0, 0.0, 5.0) == "cold"


def test_resolve_city_default_seoul() -> None:
    city = lc.load_city("Seoul")
    assert city["label_ko"] == "서울"
    assert city["latitude"] == 37.5665
