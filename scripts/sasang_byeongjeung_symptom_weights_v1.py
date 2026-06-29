# -*- coding: utf-8 -*-
"""병증약리 symptom reference weights v1 — 정충·부종 (B-track, wellness filter only)."""

from __future__ import annotations

from typing import Any

SCHEMA_ID = "sasang_byeongjeung_symptom_weights_v1"
VERSION = "1.0.0"

# Literature-informed reference priorities [HYPO] — not diagnostic thresholds.
_SYMPTOM_DEFS: tuple[dict[str, Any], ...] = (
    {
        "symptom_id": "jeongchung",
        "label_ko": "정충",
        "label_en": "cold_excess_pattern",
        "reading_ko": (
            "한·냉·수족냉·소화저하 축의 문헌·코호트 참고 우선순위. "
            "단일 증상으로 체질·처방을 확정하지 않습니다."
        ),
    },
    {
        "symptom_id": "bujong",
        "label_ko": "부종",
        "label_en": "edema_swelling_pattern",
        "reading_ko": (
            "체중 변화 대비 부종·수분 저류 축의 문헌·코호트 참고 우선순위. "
            "시장·레짐 지표와 자동 대응시키지 않습니다."
        ),
    },
)

# Per-constitution reference weights (0–1); sum not required — human reads table only.
_BY_CONSTITUTION: dict[str, dict[str, Any]] = {
    "soeum_in": {
        "label_ko": "소음인",
        "weights": {"jeongchung": 0.85, "bujong": 0.35},
        "priority_axis_ko": "비·신 한열 — 정충 문진 우선",
    },
    "taeeum_in": {
        "label_ko": "태음인",
        "weights": {"jeongchung": 0.45, "bujong": 0.80},
        "priority_axis_ko": "폐·간 축 — 부종·수분 패턴 문진 우선 (KoGES MetS 참고)",
    },
    "soyang_in": {
        "label_ko": "소양인",
        "weights": {"jeongchung": 0.55, "bujong": 0.50},
        "priority_axis_ko": "한열 교차 — 정충·부종 병치",
    },
    "taeyang_in": {
        "label_ko": "태양인",
        "weights": {"jeongchung": 0.60, "bujong": 0.40},
        "priority_axis_ko": "표열·신수 — 희소 코호트 불확실도 상향",
        "uncertainty_boost": True,
    },
}

_TY_SPARSITY = {
    "cohort_pct_range": [0.0003, 0.022],
    "standardized_under_pct": 0.001,
    "koges_excluded_in_literature": True,
    "risk_weight_boost": 1.25,
    "note_ko": (
        "[HYPO] TY 희소성 ↔ 금화교역 경계 레짐 은유는 FOUR_LENS §heuristic; "
        "임상 단정·자동 트리거 금지."
    ),
}

_ANCHORS: tuple[dict[str, str], ...] = (
    {
        "kind": "literature",
        "ref": "KCMB 2015 TY prevalence 0.03–2.2%",
        "note_ko": "코호트별 TY 비율 — A-tier 임상 한정",
    },
    {
        "kind": "literature",
        "ref": "PMC2741626 KoGES TY exclusion",
        "note_ko": "표본 부족 시 TY 통계 제외 처리",
    },
    {
        "kind": "repo_path",
        "ref": "docs/research/FOUR_LENS_YINYANG_REGULARIZATION_V1.md",
        "note_ko": "5-slot adoptable slot #1",
    },
    {
        "kind": "repo_path",
        "ref": "docs/final/MKM_COMPUTATIONAL_SASANG_DECLARATION_V1.md",
        "note_ko": "TY risk-weight 설계·선언",
    },
)


def build_symptom_weights_v1() -> dict[str, Any]:
    """Deterministic symptom reference table for interpretive bundle (human_only)."""
    return {
        "schema": SCHEMA_ID,
        "version": VERSION,
        "track": "B",
        "research_only": True,
        "auto_clinical_trigger": False,
        "filter_mode": "wellness_reference_only",
        "symptoms": [dict(s) for s in _SYMPTOM_DEFS],
        "by_constitution": {k: dict(v) for k, v in _BY_CONSTITUTION.items()},
        "ty_sparsity": dict(_TY_SPARSITY),
        "anchors": [dict(a) for a in _ANCHORS],
        "disclaimer_ko": (
            "정충·부종 가중치는 『문진·생활 조율 참고 순서』이며 진단·처방·실매매 트리거가 아닙니다."
        ),
    }
