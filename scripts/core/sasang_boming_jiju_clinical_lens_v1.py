# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.55, L:0.62, K:0.78, M:0.40}
# Balance: 86
# Purpose: Per-constitution 보명지주 clinical lens pack (B-track, non-Rx).
"""sasang_boming_jiju_clinical_lens_v1 — 체질별 보명지주·원전 포인터 2차 패킹."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.core.sasang_cross_ref_deep_link_v1 import (
    deep_links_for_constitution,
    render_deep_links_markdown,
)
from scripts.core.scm_boming_jiju_lexicon_v1 import DEFAULT_LEXICON_PATH, entries_by_constitution

_ROOT = Path(__file__).resolve().parents[2]
INTERPRETIVE_BUNDLE = _ROOT / "docs" / "final" / "artifacts" / "sasang_interpretive_insight_bundle_v1_latest.json"
CROSS_REF_DRAFT = _ROOT / "docs" / "final" / "artifacts" / "SASANG_CROSS_REF_DRAFT.json"

SCHEMA_ID = "sasang_boming_jiju_clinical_lens_pack_v1"

KO_LABEL_TO_ID: dict[str, str] = {
    "태음인": "taeeum_in",
    "태양인": "taeyang_in",
    "소음인": "soeum_in",
    "소양인": "soyang_in",
}

CONSTITUTION_STATIC: dict[str, dict[str, Any]] = {
    "soeum_in": {
        "organ_axis_ko": "腎大脾小 (비·신 축)",
        "byeongjeung_reading_axes_ko": [
            "胃受寒表證 vs 腎受熱表證 감별",
            "표·裏 한열과 비위·신수 축",
        ],
        "literature_pointers": [
            {
                "title_ko": "동의수세보원 ⟪소음인병론⟫",
                "ref": "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json (section_key=soeum)",
                "note_ko": "[HYPO] 원전 교차 초안 — 근거 행·문헌 확인 후 인용",
            }
        ],
        "clinical_priority_questions": [
            {
                "axis_ko": "소화·한열",
                "prompt_ko": "비위 고갈·수족냉증이 동시에 있으면 위수한표증·망양(亡陽) 전조 여부를 우선 문진",
                "confirm_question_ko": "찬물·찬음식 후 즉시 복만·설사·한증 악화가 있습니까?",
                "trigger_keywords": ["소화", "복만", "냉", "수족", "설사", "한"],
            },
            {
                "axis_ko": "심화·기울",
                "prompt_ko": "상열·심계와 소화불량이 겹치면 심화하강 불능·기울성 소화마비 가능성 검토",
                "confirm_question_ko": "스트레스·긴장 시 명치 막힘과 두근거림이 동반됩니까?",
                "trigger_keywords": ["심계", "두근", "스트레스", "불면", "명치"],
            },
        ],
        "yakri_lexicon_scan_ko": [
            "인삼(人蔘) — 문헌 참조용",
            "백하수오(白何首烏) — 문헌 참조용",
            "건강(乾薑) — 문헌 참조용",
        ],
    },
    "taeeum_in": {
        "organ_axis_ko": "肺大肝小 (폐·간 축)",
        "byeongjeung_reading_axes_ko": ["표한·위완수한", "열·담음 경로"],
        "literature_pointers": [
            {
                "title_ko": "동의수세보원 ⟪태음인병론⟫",
                "ref": "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json (section_key=taeeum)",
                "note_ko": "[HYPO] 원전 교차 초안",
            }
        ],
        "clinical_priority_questions": [
            {
                "axis_ko": "호흡·열",
                "prompt_ko": "폐열·담음·피부 소양 변증 우선",
                "confirm_question_ko": "가래·기침·안면 홍조·갈증 패턴이 두드러집니까?",
                "trigger_keywords": ["기침", "가래", "열", "갈", "피부"],
            },
        ],
        "yakri_lexicon_scan_ko": ["호산지기 관련 문헌 앵커 — 자동 처방 금지"],
    },
    "soyang_in": {
        "organ_axis_ko": "脾大胃小 (비·위 축)",
        "byeongjeung_reading_axes_ko": ["표한·비수한", "열·한 교차"],
        "literature_pointers": [
            {
                "title_ko": "동의수세보원 ⟪소양인병론⟫",
                "ref": "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json (section_key=soyang)",
                "note_ko": "[HYPO] 원전 교차 초안",
            }
        ],
        "clinical_priority_questions": [
            {
                "axis_ko": "한열·소화",
                "prompt_ko": "표한·비수한과 위열 교차 여부",
                "confirm_question_ko": "한증과 소화불량이 교대로 나타납니까?",
                "trigger_keywords": ["한", "소화", "복통"],
            },
        ],
        "yakri_lexicon_scan_ko": ["담기 관련 문헌 앵커 — 자동 처방 금지"],
    },
    "taeyang_in": {
        "organ_axis_ko": "脾大胃小·태양 특성 (위·비·신 축)",
        "byeongjeung_reading_axes_ko": ["표증·열증", "신수·위열"],
        "literature_pointers": [
            {
                "title_ko": "동의수세보원 ⟪태양인병론⟫",
                "ref": "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json (section_key=taeyang)",
                "note_ko": "[HYPO] 원전 교차 초안",
            }
        ],
        "clinical_priority_questions": [
            {
                "axis_ko": "열·신수",
                "prompt_ko": "태양 표증·신수열 변증 감별",
                "confirm_question_ko": "갈·번갈·요통·소변 이상이 동반됩니까?",
                "trigger_keywords": ["열", "갈", "요통", "소변"],
            },
        ],
        "yakri_lexicon_scan_ko": ["심기 관련 문헌 앵커 — 자동 처방 금지"],
    },
}


def resolve_constitution_id(label: str) -> str | None:
    """Map Korean 체질 label (with optional parenthetical) to lexicon id."""
    raw = (label or "").strip()
    if not raw:
        return None
    head = re.split(r"[\s(（]", raw, maxsplit=1)[0].strip()
    if head in KO_LABEL_TO_ID:
        return KO_LABEL_TO_ID[head]
    for ko, cid in KO_LABEL_TO_ID.items():
        if ko in raw:
            return cid
    return None


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


_ROLE_SORT = {
    "boming_jiju": 0,
    "yakri_anchor": 1,
    "byeongjeung_axis": 2,
    "scm_domain_token": 3,
    "ijeoma_harvest": 4,
}


def _boming_terms_for(constitution_id: str, lexicon_path: Path | None = None) -> list[dict[str, Any]]:
    grouped = entries_by_constitution(lexicon_path)
    rows = grouped.get(constitution_id) or []
    out: list[dict[str, Any]] = []
    for e in sorted(
        rows,
        key=lambda x: (
            _ROLE_SORT.get(str(x.get("pillar_role")), 5),
            -int(x.get("priority") or 0),
            str(x.get("term", "")),
        ),
    ):
        if str(e.get("pillar_role")) == "constitution_label":
            continue
        out.append(
            {
                "term": e.get("term"),
                "priority": e.get("priority"),
                "notes": e.get("notes"),
                "pillar_role": e.get("pillar_role"),
            }
        )
    return out


def build_constitution_slice(
    constitution_id: str,
    *,
    lexicon_path: Path | None = None,
    cross_ref_deep_link_limit: int = 5,
) -> dict[str, Any]:
    static = CONSTITUTION_STATIC.get(constitution_id, {})
    label_ko = next((k for k, v in KO_LABEL_TO_ID.items() if v == constitution_id), constitution_id)
    deep_links = deep_links_for_constitution(constitution_id, limit=cross_ref_deep_link_limit)
    lit = list(static.get("literature_pointers") or [])
    if deep_links:
        top = deep_links[0]
        lit.append(
            {
                "title_ko": lit[0].get("title_ko") if lit else f"동의수세보원 · {label_ko}",
                "ref": top.get("deep_link_uri"),
                "note_ko": f"[HYPO] {top.get('entry_id')} · {top.get('satellite_ref', '')[:80]}",
            }
        )
    return {
        "label_ko": label_ko,
        "constitution_id": constitution_id,
        "organ_axis_ko": static.get("organ_axis_ko", ""),
        "boming_jiju_terms": _boming_terms_for(constitution_id, lexicon_path),
        "byeongjeung_reading_axes_ko": list(static.get("byeongjeung_reading_axes_ko") or []),
        "literature_pointers": lit,
        "cross_ref_deep_links": deep_links,
        "clinical_priority_questions": list(static.get("clinical_priority_questions") or []),
        "yakri_lexicon_scan_ko": list(static.get("yakri_lexicon_scan_ko") or []),
    }


def build_full_pack(*, lexicon_path: Path | None = None) -> dict[str, Any]:
    lp = lexicon_path or DEFAULT_LEXICON_PATH
    constitutions = {
        cid: build_constitution_slice(cid, lexicon_path=lp) for cid in KO_LABEL_TO_ID.values()
    }
    return {
        "schema": SCHEMA_ID,
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "boundary_contract": {
            "track": "B",
            "research_only": True,
            "auto_prescription_forbidden": True,
            "physician_final_authority": True,
        },
        "source_refs": {
            "lexicon_json": _rel(lp),
            "interpretive_bundle_json": _rel(INTERPRETIVE_BUNDLE),
            "cross_ref_draft_json": _rel(CROSS_REF_DRAFT),
        },
        "constitutions": constitutions,
        "disclaimer_ko": (
            "[B-track·HYPO] 보명지주 2차 렌즈 팩 — 문헌·진찰 우선순위 힌트만. "
            "진단·처방·탕명 자동 추천 없음. 4진 확정은 한의사만."
        ),
    }


def _symptom_blob(symptoms: list[Any], situation: str) -> str:
    parts = [str(s) for s in symptoms if s]
    if situation:
        parts.append(situation)
    return " ".join(parts)


def _active_questions(
    slice_doc: dict[str, Any],
    symptoms: list[Any],
    situation: str,
) -> list[dict[str, Any]]:
    blob = _symptom_blob(symptoms, situation)
    active: list[dict[str, Any]] = []
    for q in slice_doc.get("clinical_priority_questions") or []:
        keys = q.get("trigger_keywords") or []
        if not keys or any(k in blob for k in keys):
            active.append(q)
    return active


def render_markdown_section(
    label: str,
    symptoms: list[Any] | None = None,
    situation: str = "",
    *,
    pack: dict[str, Any] | None = None,
    lexicon_path: Path | None = None,
) -> str:
    """Markdown block for patient_intake sasang slot (2nd packing)."""
    cid = resolve_constitution_id(label)
    if not cid:
        return (
            "## [HYPO] 보명지주 2차 렌즈 팩\n\n"
            f"- 체질 라벨 `{label}` 을 4체질 키로 해석하지 못했습니다. "
            "태음인/태양인/소음인/소양인 중 하나로 정규화 후 재실행하십시오.\n"
        )
    full = pack or build_full_pack(lexicon_path=lexicon_path)
    sl = full.get("constitutions", {}).get(cid) or {}
    syms = symptoms or []
    active_q = _active_questions(sl, syms, situation)

    lines = [
        "## [HYPO] 보명지주·원전 2차 렌즈 팩 (B-track)",
        "",
        full.get("disclaimer_ko", ""),
        "",
        f"### 체질 슬라이스: **{sl.get('label_ko')}** (`{cid}`)",
        f"- 장부 축 힌트: {sl.get('organ_axis_ko', '—')}",
        "",
        "#### 보명지주 렉시콘 앵커 (`scm_boming_jiju_lexicon_v1`)",
    ]
    terms = sl.get("boming_jiju_terms") or []
    if terms:
        curated = [t for t in terms if str(t.get("pillar_role")) != "ijeoma_harvest"][:10]
        harvest_extra = [t for t in terms if str(t.get("pillar_role")) == "ijeoma_harvest"][:4]
        for t in curated + harvest_extra:
            role = t.get("pillar_role") or "—"
            lines.append(f"- **{t.get('term')}** — {t.get('notes') or role}")
        if len(terms) > len(curated) + len(harvest_extra):
            lines.append(f"- *(lexicon 총 {len(terms)}건 — 상위만 표시, 전체는 SSOT JSON)*")
    else:
        lines.append("- *(해당 체질 보명지주 항목 없음 — lexicon 갱신 필요)*")

    lines.extend(["", "#### 병증·약리 읽기 축 (문헌语境, 자동 처방 금지)"])
    for ax in sl.get("byeongjeung_reading_axes_ko") or []:
        lines.append(f"- {ax}")

    lines.extend(["", "#### 원전 포인터"])
    for lp in sl.get("literature_pointers") or []:
        lines.append(f"- {lp.get('title_ko')}: `{lp.get('ref')}` — {lp.get('note_ko', '')}")

    deep_links = sl.get("cross_ref_deep_links") or []
    if deep_links:
        lines.extend(["", "#### 원전 deep link (`SASANG_CROSS_REF_DRAFT`)"])
        lines.append(render_deep_links_markdown(deep_links))

    lines.extend(["", "#### 진찰 우선 문진 리스트 (증상 연동)"])
    if active_q:
        for q in active_q:
            lines.append(f"- **[{q.get('axis_ko')}]** {q.get('prompt_ko')}")
            cq = q.get("confirm_question_ko")
            if cq:
                lines.append(f"  - 확인: {cq}")
    else:
        lines.append("- *(증상 키워드 미매칭 — 전체 축은 슬라이스 정의 참고)*")

    yakri = sl.get("yakri_lexicon_scan_ko") or []
    if yakri:
        lines.extend(["", "#### 약리 스캔 키워드 (문헌 교차만)"])
        for y in yakri:
            lines.append(f"- {y}")

    lines.extend(
        [
            "",
            "#### SSOT 링크",
            f"- 렉시콘: `{full.get('source_refs', {}).get('lexicon_json')}`",
            f"- 통찰 번들: `{full.get('source_refs', {}).get('interpretive_bundle_json')}`",
            f"- 교차 초안: `{full.get('source_refs', {}).get('cross_ref_draft_json')}`",
        ]
    )
    return "\n".join(lines)
