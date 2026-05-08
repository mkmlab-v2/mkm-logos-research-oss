from __future__ import annotations

from scripts.myeongni_lens_v1.mkm_myeongni_math import compute_mkm_myeongni_math


def test_mkm_myeongni_math_computes_ten_god_and_arbitration():
    advanced = {
        "pillars": {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "壬子"},
        "sajeong_interpolation": {"寅": ["甲", "丙", "戊"], "子": ["癸"]},
        "school_signals": [
            {"school_id": "zi_ping", "direction_hint": 0.2, "confidence_hint": 0.6},
            {"school_id": "zi_wei", "direction_hint": -0.3, "confidence_hint": 0.55},
        ],
        "school_blend": {"direction_score": 0.05, "confidence": 0.58},
    }
    out = compute_mkm_myeongni_math(advanced)
    assert out["status"] == "ok"
    assert out["day_master_stem"] == "戊"
    assert "surface_ten_god_counts" in out
    assert "hidden_ten_god_counts" in out
    assert -1.0 <= float(out["arbitrated_direction_score"]) <= 1.0
    assert 0.05 <= float(out["arbitrated_confidence"]) <= 0.95


def test_mkm_myeongni_math_accepts_hangul_pillar_stems():
    """PerfectManseryeok emits Hangul 천간; math layer must still resolve 일간."""
    advanced = {
        "pillars": {"year": "갑자", "month": "병인", "day": "무오", "hour": "임자"},
        "sajeong_interpolation": {},
        "school_signals": [],
        "school_blend": {"direction_score": 0.0, "confidence": 0.5},
    }
    out = compute_mkm_myeongni_math(advanced)
    assert out["status"] == "ok"
    assert out.get("day_master_stem") == "戊"


def test_mkm_myeongni_math_handles_missing_day_stem():
    out = compute_mkm_myeongni_math(
        {
            "pillars": {"day": ""},
            "sajeong_interpolation": {},
            "school_signals": [{"direction_hint": 0.1}],
        }
    )
    assert out["status"] == "insufficient_day_stem"
