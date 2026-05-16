# -*- coding: utf-8 -*-
import json

from scripts.build_myeongni_full_report_v1 import _build_report


def test_build_from_inline_birth_minimal():
    birth = {
        "schema": "saju_global_birth_result_v1",
        "version": "1.0.0",
        "resolution": {
            "birth_instant_utc": "1973-12-09T19:30:00Z",
            "iana_tz": "Asia/Seoul",
            "local_iso": "1973-12-10T04:30:00+09:00",
            "engine_inputs": {"year": 1973, "month": 12, "day": 10, "hour": 4},
            "warnings": [],
            "meta": {},
        },
        "full_saju": {
            "saju": {"year": "계축", "month": "갑자", "day": "경진", "hour": "무인"},
            "ilgan": "경",
            "daewoon": [
                {
                    "age_start": 0.0,
                    "age_end": 10.0,
                    "saju": "갑자",
                    "cycle": 1,
                    "direction": "backward",
                    "schema": "daewoon_v1",
                    "qiyun_applied": True,
                }
            ],
            "daewoon_qiyun_v1": {"forward": False, "method": "meeus_sun_lon_jie_v1"},
            "calculation_method": "calculation_fallback",
            "verification": {},
            "birth_info": {},
            "note": "",
            "calculated_at": "",
        },
    }
    r = _build_report(birth, 2026, 3, 2)
    assert r["schema"] == "myeongni_full_report_v1"
    assert r["pillars"]["hour"] == "무인"
    assert r["daewoon"]["cycles"][0]["pillar"] == "갑자"
    assert len(r["annual_fortune"]["rows"]) == 3
    assert len(r["monthly_fortune"]["rows"]) == 6
    s = r["structure_analysis"]["school_conflict_resolution_v1"]
    assert s["schema"] == "myeongni_school_conflict_resolution_v1"
    assert s["decision"] in {"balance_centered", "flow_centered", "hybrid_guarded"}
    yh = r["structure_analysis"]["yongsin_hypothesis_candidates_v1"]
    assert yh["schema"] == "myeongni_yongsin_hypothesis_candidates_v1"
    assert yh["research_only"] is True
    assert yh["machine_final_yongsin"] == "forbidden"
    assert yh["school_decision_echo"] == s["decision"]
    cands = yh["candidates"]
    assert len(cands) == 5
    assert {c["element_oheng"] for c in cands} == {"목", "화", "토", "금", "수"}
    assert cands[0]["rank"] == 1
    assert isinstance(cands[0]["hypothesis_score"], (int, float))
    assert cands[0]["element_oheng"] == "화"
    assert yh["evidence_tier"] == "heuristic_only"
    assert yh["formula_version"] == "yongsin_hypothesis_v1.0.0-heuristic"
    fp = yh["derivation_fingerprint"]
    assert isinstance(fp, str) and len(fp) == 64 and all(c in "0123456789abcdef" for c in fp)


def test_yongsin_derivation_fingerprint_stable_across_annual_window():
    birth = {
        "schema": "saju_global_birth_result_v1",
        "version": "1.0.0",
        "resolution": {
            "birth_instant_utc": "1973-12-09T19:30:00Z",
            "iana_tz": "Asia/Seoul",
            "local_iso": "1973-12-10T04:30:00+09:00",
            "engine_inputs": {"year": 1973, "month": 12, "day": 10, "hour": 4},
            "warnings": [],
            "meta": {},
        },
        "full_saju": {
            "saju": {"year": "계축", "month": "갑자", "day": "경진", "hour": "무인"},
            "ilgan": "경",
            "daewoon": [
                {
                    "age_start": 0.0,
                    "age_end": 10.0,
                    "saju": "갑자",
                    "cycle": 1,
                    "direction": "backward",
                    "schema": "daewoon_v1",
                    "qiyun_applied": True,
                }
            ],
            "daewoon_qiyun_v1": {"forward": False, "method": "meeus_sun_lon_jie_v1"},
            "calculation_method": "calculation_fallback",
            "verification": {},
            "birth_info": {},
            "note": "",
            "calculated_at": "",
        },
    }
    r_a = _build_report(birth, 2026, 3, 2)
    r_b = _build_report(birth, 2019, 1, 1)
    fp_a = r_a["structure_analysis"]["yongsin_hypothesis_candidates_v1"]["derivation_fingerprint"]
    fp_b = r_b["structure_analysis"]["yongsin_hypothesis_candidates_v1"]["derivation_fingerprint"]
    assert fp_a == fp_b
