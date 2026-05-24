# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.50, L:0.58, K:0.75, M:0.42}
# Balance: 85
# Purpose: [HYPO] 선천 명리 표면 vs 진찰 확정 체질 교차검증 한 줄 (비임상).
"""patient_intake_myeongni_sasang_cross_v1 — 명리·사상 삼각검증 보조."""

from __future__ import annotations

from typing import Any

from scripts.core.sasang_boming_jiju_clinical_lens_v1 import resolve_constitution_id

# [HYPO] 문헌·장부 축 힌트만 — 임상 체질 확정을 대체하지 않음.
_CONSTITUTION_ELEMENT_HINT: dict[str, dict[str, Any]] = {
    "soeum_in": {
        "label_ko": "소음인",
        "weak_elements": ["토", "수"],
        "stress_elements": ["화"],
        "organ_axis_ko": "비·신 (脾腎)",
    },
    "taeeum_in": {
        "label_ko": "태음인",
        "weak_elements": ["금", "목"],
        "stress_elements": ["화"],
        "organ_axis_ko": "폐·간 (肺肝)",
    },
    "soyang_in": {
        "label_ko": "소양인",
        "weak_elements": ["토", "목"],
        "stress_elements": ["화", "수"],
        "organ_axis_ko": "비·위 (脾胃)",
    },
    "taeyang_in": {
        "label_ko": "태양인",
        "weak_elements": ["수", "토"],
        "stress_elements": ["화"],
        "organ_axis_ko": "신·위·비 (太陽)",
    },
}

_ELEMENT_KO_TO_HANJA = {"목": "木", "화": "火", "토": "土", "금": "金", "수": "水"}


def _element_profile_from_report(report: dict[str, Any]) -> dict[str, Any]:
    sa = report.get("structure_analysis") or {}
    return sa.get("element_profile") or {}


def _day_master_element(report: dict[str, Any]) -> str:
    dm = report.get("day_master") or {}
    hint = str(dm.get("stem_element_hint") or "")
    for ko, _ in _ELEMENT_KO_TO_HANJA.items():
        if ko in hint:
            return ko
    return ""


def assess_myeongni_sasang_cross(
    myeongni_report: dict[str, Any],
    clinical_sasang_label: str,
) -> dict[str, Any]:
    """
    [HYPO] 진찰 확정 체질 vs 명리 element_profile 표면 교차.
    Returns status: match | partial | mismatch | insufficient.
    """
    cid = resolve_constitution_id(clinical_sasang_label)
    if not cid:
        return {
            "status": "insufficient",
            "status_ko": "불충분",
            "clinical_label": clinical_sasang_label,
            "constitution_id": None,
            "signals": [],
            "note_ko": "진찰 확정 체질 라벨(태음/태양/소음/소양)이 없거나 정규화 실패.",
        }

    hint = _CONSTITUTION_ELEMENT_HINT.get(cid, {})
    ep = _element_profile_from_report(myeongni_report)
    counts = ep.get("element_counts_visible") or {}
    weakest = str(ep.get("weakest_element_visible") or "")
    dominant = str(ep.get("dominant_element_visible") or "")
    dm_el = _day_master_element(myeongni_report)

    weak_set = set(hint.get("weak_elements") or [])
    stress_set = set(hint.get("stress_elements") or [])
    signals: list[str] = []
    score = 0

    if weakest and weakest in weak_set:
        score += 2
        signals.append(f"약세(visible) `{weakest}` ∈ 체질 힌트 약세축")
    elif weakest:
        signals.append(f"약세(visible) `{weakest}` — 체질 힌트 약세축과 불일치(교차 문진 권장)")

    if dominant and dominant in weak_set:
        score += 1
        signals.append(f"우세(visible) `{dominant}` 가 체질 약세축과 겹침(부담 축)")
    if dm_el and dm_el in weak_set:
        score += 1
        signals.append(f"일간 오행 `{dm_el}` ∈ 체질 힌트 약세축")

    if dominant and dominant in stress_set and dominant not in weak_set:
        score -= 1
        signals.append(f"우세 `{dominant}` 가 stress 축 — 상열·교란 변수 [HYPO]")

    if score >= 2:
        status, status_ko = "match", "일치(표면)"
    elif score == 1:
        status, status_ko = "partial", "부분 일치"
    elif score <= 0 and weakest and weakest not in weak_set and dominant not in weak_set:
        status, status_ko = "mismatch", "불일치(표면)"
    else:
        status, status_ko = "partial", "부분 일치"

    return {
        "status": status,
        "status_ko": status_ko,
        "clinical_label": clinical_sasang_label,
        "constitution_id": cid,
        "organ_axis_hint_ko": hint.get("organ_axis_ko", ""),
        "element_surface": {
            "counts_visible": counts,
            "weakest_visible": weakest,
            "dominant_visible": dominant,
            "day_master_element": dm_el,
        },
        "hint_weak_elements": sorted(weak_set),
        "signals": signals,
        "note_ko": (
            "[HYPO·research_only] 명리 가시 오행·일간과 진찰 확정 체질의 통계적 정합 힌트만. "
            "임상 변증·체질 확정을 대체하지 않음."
        ),
    }


def render_cross_check_markdown(
    myeongni_report: dict[str, Any],
    clinical_sasang_label: str,
) -> str:
    doc = assess_myeongni_sasang_cross(myeongni_report, clinical_sasang_label)
    ep = doc.get("element_surface") or {}
    lines = [
        "### [HYPO] 선천 명리 × 진찰 확정 체질 교차검증",
        "",
        f"- **진찰 확정:** `{doc.get('clinical_label')}` (`{doc.get('constitution_id') or '—'}`)",
        f"- **교차 판정(표면):** **{doc.get('status_ko')}** (`{doc.get('status')}`)",
        f"- **장부 축 힌트:** {doc.get('organ_axis_hint_ko') or '—'}",
        f"- **가시 오행:** 우세 `{ep.get('dominant_visible') or '—'}` / 약세 `{ep.get('weakest_visible') or '—'}` "
        f"/ 일간 `{ep.get('day_master_element') or '—'}`",
    ]
    for sig in doc.get("signals") or []:
        lines.append(f"  - {sig}")
    lines.extend(["", f"- {doc.get('note_ko', '')}"])
    return "\n".join(lines)
