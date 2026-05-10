from __future__ import annotations

import math
from typing import Any

STEM_META: dict[str, tuple[str, str]] = {
    "甲": ("wood", "yang"),
    "乙": ("wood", "yin"),
    "丙": ("fire", "yang"),
    "丁": ("fire", "yin"),
    "戊": ("earth", "yang"),
    "己": ("earth", "yin"),
    "庚": ("metal", "yang"),
    "辛": ("metal", "yin"),
    "壬": ("water", "yang"),
    "癸": ("water", "yin"),
}

# PerfectManseryeok / fusion_bridge pillars use Hangul 천간 (갑을병정무기경신임계).
_HANGUL_STEM_TO_HANZI: dict[str, str] = {
    "갑": "甲",
    "을": "乙",
    "병": "丙",
    "정": "丁",
    "무": "戊",
    "기": "己",
    "경": "庚",
    "신": "辛",
    "임": "壬",
    "계": "癸",
}


def _canonical_stem_char(ch: str) -> str:
    """Hangul 천간 → 한자 STEM_META 키 (이미 한자면 그대로)."""
    if not ch:
        return ""
    return _HANGUL_STEM_TO_HANZI.get(ch, ch)

ELEMENT_PRODUCES = {
    "wood": "fire",
    "fire": "earth",
    "earth": "metal",
    "metal": "water",
    "water": "wood",
}
ELEMENT_CONTROLS = {
    "wood": "earth",
    "fire": "metal",
    "earth": "water",
    "metal": "wood",
    "water": "fire",
}


def _first_char(v: Any) -> str:
    s = str(v or "").strip()
    return s[:1] if s else ""


def _extract_surface_stems(pillars: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for k in ("year", "month", "day", "hour"):
        ch = _canonical_stem_char(_first_char(pillars.get(k)))
        if ch in STEM_META:
            out.append(ch)
    return out


def _extract_hidden_stems(sajeong: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if not isinstance(sajeong, dict):
        return out
    for v in sajeong.values():
        if isinstance(v, dict):
            hs = v.get("hidden_gans")
            if isinstance(hs, list):
                for x in hs:
                    ch = _canonical_stem_char(_first_char(x))
                    if ch in STEM_META:
                        out.append(ch)
        elif isinstance(v, list):
            for x in v:
                ch = _canonical_stem_char(_first_char(x))
                if ch in STEM_META:
                    out.append(ch)
    return out


def _ten_god_name(day_stem: str, target_stem: str) -> str:
    de, dp = STEM_META[day_stem]
    te, tp = STEM_META[target_stem]
    same_polarity = dp == tp

    if te == de:
        return "bi_gyeon" if same_polarity else "geop_jae"
    if ELEMENT_PRODUCES[de] == te:
        return "sik_sin" if same_polarity else "sang_gwan"
    if ELEMENT_CONTROLS[de] == te:
        return "pyeon_jae" if same_polarity else "jeong_jae"
    if ELEMENT_CONTROLS[te] == de:
        return "pyeon_gwan" if same_polarity else "jeong_gwan"
    if ELEMENT_PRODUCES[te] == de:
        return "pyeon_in" if same_polarity else "jeong_in"
    return "unknown"


def _count_ten_gods(day_stem: str, stems: list[str]) -> dict[str, int]:
    keys = [
        "bi_gyeon",
        "geop_jae",
        "sik_sin",
        "sang_gwan",
        "pyeon_jae",
        "jeong_jae",
        "pyeon_gwan",
        "jeong_gwan",
        "pyeon_in",
        "jeong_in",
    ]
    out = {k: 0 for k in keys}
    for st in stems:
        tg = _ten_god_name(day_stem, st)
        if tg in out:
            out[tg] += 1
    return out


def _school_disagreement_index(signals: list[dict[str, Any]]) -> float:
    vals = [float(s.get("direction_hint") or 0.0) for s in signals if isinstance(s, dict)]
    if len(vals) <= 1:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / len(vals)
    sd = math.sqrt(var)
    return max(0.0, min(1.0, sd))


def compute_mkm_myeongni_math(advanced: dict[str, Any]) -> dict[str, Any]:
    pillars = advanced.get("pillars") if isinstance(advanced.get("pillars"), dict) else {}
    sajeong = (
        advanced.get("sajeong_interpolation")
        if isinstance(advanced.get("sajeong_interpolation"), dict)
        else {}
    )
    signals = advanced.get("school_signals") if isinstance(advanced.get("school_signals"), list) else []

    day_stem = _canonical_stem_char(_first_char(pillars.get("day")))
    if day_stem not in STEM_META:
        return {
            "status": "insufficient_day_stem",
            "arbitrated_direction_score": 0.0,
            "arbitrated_confidence": 0.35,
            "school_disagreement_index": _school_disagreement_index(signals),
        }

    surface = _extract_surface_stems(pillars)
    hidden = _extract_hidden_stems(sajeong)
    surface_counts = _count_ten_gods(day_stem, surface)
    hidden_counts = _count_ten_gods(day_stem, hidden)

    output_score = surface_counts["sik_sin"] + surface_counts["sang_gwan"]
    resource_score = surface_counts["pyeon_in"] + surface_counts["jeong_in"]
    officer_score = hidden_counts["pyeon_gwan"] + hidden_counts["jeong_gwan"]
    wealth_score = hidden_counts["pyeon_jae"] + hidden_counts["jeong_jae"]
    hidden_total = max(1, len(hidden))
    surface_total = max(1, len(surface))

    ten_god_balance = (output_score - resource_score) / float(surface_total)
    jijangan_pressure = (officer_score + wealth_score) / float(hidden_total)
    disagreement = _school_disagreement_index(signals)

    school_blend = advanced.get("school_blend") if isinstance(advanced.get("school_blend"), dict) else {}
    d_school = float(school_blend.get("direction_score") or 0.0)
    c_school = float(school_blend.get("confidence") or 0.5)

    # MKM arbitration: keep school blend as base and adjust by ten-god balance + hidden pressure.
    d_adj = (0.22 * ten_god_balance) - (0.18 * jijangan_pressure)
    d_out = max(-1.0, min(1.0, d_school + d_adj))
    c_out = max(0.05, min(0.95, c_school * (1.0 - 0.35 * disagreement)))

    return {
        "status": "ok",
        "day_master_stem": day_stem,
        "surface_ten_god_counts": surface_counts,
        "hidden_ten_god_counts": hidden_counts,
        "ten_god_balance": round(ten_god_balance, 6),
        "jijangan_pressure": round(jijangan_pressure, 6),
        "school_disagreement_index": round(disagreement, 6),
        "arbitrated_direction_score": round(d_out, 6),
        "arbitrated_confidence": round(c_out, 6),
        "formula": "d_out = clamp(d_school + 0.22*ten_god_balance - 0.18*jijangan_pressure), c_out = c_school*(1-0.35*disagreement)",
    }


_EL_KO = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}


def compute_quant_profile_v0(advanced: dict[str, Any]) -> dict[str, Any]:
    """B-track 정량 블록: 천간·지장간 근거 오행 분포·십성 분포 스냅샷(관측 전용, 비임상·비실매매)."""
    disclaimer_ko = (
        "B-track 정량 스냅샷; 임상·실거래·단일 방향 단정 아님."
    )
    pillars = advanced.get("pillars") if isinstance(advanced.get("pillars"), dict) else {}
    sajeong = (
        advanced.get("sajeong_interpolation")
        if isinstance(advanced.get("sajeong_interpolation"), dict)
        else {}
    )
    day_stem = _canonical_stem_char(_first_char(pillars.get("day")))
    surface = _extract_surface_stems(pillars)
    hidden = _extract_hidden_stems(sajeong)

    elem_counts = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    for st in surface + hidden:
        if st in STEM_META:
            el_en = STEM_META[st][0]
            ko = _EL_KO.get(el_en)
            if ko:
                elem_counts[ko] += 1

    total_el = sum(elem_counts.values())
    if total_el <= 0:
        mass = {"목": 0.2, "화": 0.2, "토": 0.2, "금": 0.2, "수": 0.2}
    else:
        mass = {k: round(elem_counts[k] / float(total_el), 6) for k in elem_counts}

    ps = [mass[k] for k in ("목", "화", "토", "금", "수")]
    h = -sum(p * math.log(p + 1e-15) for p in ps)
    h_max = math.log(5.0)
    imbalance = round(1.0 - (h / h_max if h_max > 0 else 0.0), 6)
    excess_deficit = {k: round(mass[k] - 0.2, 6) for k in mass}

    ten_keys = [
        "bi_gyeon",
        "geop_jae",
        "sik_sin",
        "sang_gwan",
        "pyeon_jae",
        "jeong_jae",
        "pyeon_gwan",
        "jeong_gwan",
        "pyeon_in",
        "jeong_in",
    ]
    if day_stem not in STEM_META:
        ten_norm = {k: 0.1 for k in ten_keys}
        dominance = 0.1
        tg_status = "insufficient_day_stem"
    else:
        surf_c = _count_ten_gods(day_stem, surface)
        hid_c = _count_ten_gods(day_stem, hidden)
        combined = {k: surf_c[k] + hid_c[k] for k in surf_c}
        tot_tg = sum(combined.values()) or 1
        ten_norm = {k: round(combined[k] / float(tot_tg), 6) for k in combined}
        dominance = round(max(ten_norm.values()), 6)
        tg_status = "ok"

    return {
        "schema": "myeongni_b_track_quant_block_v0",
        "status": tg_status,
        "disclaimer_ko": disclaimer_ko,
        "five_element_mass_vector_v0": mass,
        "five_element_imbalance_entropy_0_1": imbalance,
        "five_element_excess_deficit_proxy_v0": excess_deficit,
        "ten_god_strength_vector_v0": ten_norm,
        "ten_god_dominance_index_0_1": dominance,
        "stem_branch_element_lock_flags_v0": {},
        "quant_provenance_v0": {
            "normalization": (
                "five_element_L1_from_stem_element_counts; "
                "ten_god_L1_from_surface_plus_hidden_counts"
            ),
            "engine_component": "mkm_myeongni_math.compute_quant_profile_v0",
            "schema_version": "0.1.0",
        },
    }
