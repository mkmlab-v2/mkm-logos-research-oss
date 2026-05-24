#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intake JSON + birth clock → SOAP draft + `patient_care_bundle_v1`.

**기본:** **Track B** 레일 명시 · `[HYPO]` 정보 **최대 밀도** (원장 adjudication 용).
`--brief-output`: 짧은 초기 스타일. 슬롯 마크다운 초과분은 자동 잘림.

SSOT: `patient_care_bundle_v1.schema.json`, boundary contract in bundle JSON.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCHEMA_BUNDLE = ROOT / "docs" / "final" / "schemas" / "patient_care_bundle_v1.schema.json"
SCHEMA_INTAKE = ROOT / "docs" / "final" / "schemas" / "patient_intake_fusion_draft_input_v1.schema.json"
ASSEMBLE_PATH = ROOT / "scripts" / "assemble_patient_care_bundle_with_myeongni_v1.py"
APPLY_SLOT_TEMPLATES = ROOT / "scripts" / "apply_patient_care_bundle_slot_templates_v1.py"
VALIDATE_POLICY = ROOT / "scripts" / "validate_patient_care_bundle_against_policy_v1.py"
RENDER_BUNDLE_MD = ROOT / "scripts" / "render_patient_care_bundle_markdown_v1.py"
DEFAULT_POLICY_JSON = ROOT / "docs" / "final" / "artifacts" / "patient_care_bundle_generation_policy_v1.default.json"
SLOT_TEMPLATES_JSON = ROOT / "docs" / "final" / "artifacts" / "patient_care_bundle_slot_templates_ko_v1.json"


SAJU_BIRTH_RESOLVER_PATH = ROOT / "scripts" / "saju_birth_resolver_v1.py"
CLINICAL_LENS_PACK_JSON = (
    ROOT / "docs" / "final" / "artifacts" / "sasang_boming_jiju_clinical_lens_pack_v1_latest.json"
)


def _load_saju_birth_resolver() -> Any:
    name = "saju_birth_resolver_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SAJU_BIRTH_RESOLVER_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load saju_birth_resolver_v1")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _resolve_birth_engine_tuple(profile: dict[str, Any]) -> tuple[tuple[int, int, int, int, int, int], dict[str, Any]]:
    """Return (Y,M,D,h,m,s) local wall for engine + audit meta. Prefer birth_instant_utc + iana_tz (§3.4)."""

    sbr = _load_saju_birth_resolver()
    iana_tz = str(profile.get("iana_tz") or "Asia/Seoul")
    biu = str(profile.get("birth_instant_utc") or "").strip()
    if biu:
        br = sbr.resolve_from_utc_instant(biu, iana_tz)
        mode = "utc_instant_primary"
    else:
        loc = profile.get("local_birth")
        if not isinstance(loc, list) or len(loc) != 6:
            raise SystemExit(
                "profile must include birth_instant_utc+iana_tz or local_birth+iana_tz (6 ints [Y,M,D,h,m,s])"
            )
        df = int(profile.get("dst_fold") or 0)
        try:
            br = sbr.resolve_from_local_civil(
                int(loc[0]),
                int(loc[1]),
                int(loc[2]),
                int(loc[3]),
                int(loc[4]),
                int(loc[5]),
                iana_tz,
                dst_fold=df,
            )
        except ValueError as e:
            raise SystemExit(
                f"Invalid birth wall time in IANA zone (DST gap/skew): {e}. "
                "Use profile.birth_instant_utc (ISO Z) + profile.iana_tz — CONSTITUTION §3.4."
            ) from e
        mode = "local_civil_dst_fold"
    wd = br.local_datetime
    tup = (wd.year, wd.month, wd.day, wd.hour, wd.minute, wd.second)
    meta = {
        "resolution_mode": mode,
        "iana_tz_resolved": br.iana_tz,
        "birth_instant_utc_iso": br.birth_instant_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "warnings": list(br.warnings),
        "engine_local_wall_ymdhms": list(tup),
        "resolver_contract": "scripts/saju_birth_resolver_v1.py",
    }
    return tup, meta


def _load_assemble() -> Any:
    spec = importlib.util.spec_from_file_location("assemble_pcb_myeongni", ASSEMBLE_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load assemble_patient_care_bundle_with_myeongni_v1")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rel_workspace(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _soap_from_intake(intake_doc: dict[str, Any], *, dense: bool = True) -> dict[str, Any]:
    inn = intake_doc.get("intake") or {}
    symptoms = inn.get("symptoms") or []
    situation = str(inn.get("situation") or "").strip()
    notes = str(inn.get("subjective_notes") or "").strip()
    objective_draft = str(inn.get("objective_draft") or "").strip()
    se = inn.get("sasang_estimate") or {}
    label = str(se.get("label") or "미입력").strip()
    src = str(se.get("source") or "미기재").strip()

    sym_line = ", ".join(str(x) for x in symptoms) if symptoms else "미기재"

    subj = "\n".join(
        [
            "### 주관 (S) — 입력 요약 초안",
            f"- 호소·증상: {sym_line}",
            f"- 현재 상황: {situation or '미기재'}",
            f"- 기타: {notes or '—'}",
            "",
            "*임상 의미는 한의사가 확정합니다. 본 문단은 입력 정리용입니다.*",
        ]
    )
    obj_lines = [
        "### 객관 (O)",
        "- 진찰·맥·부위 소견 등: **진료 시 한의사가 확정** (입력만으로 대체하지 않음)",
        "- 입력 데이터만으로 객관 지표를 확정하지 않습니다.",
    ]
    if objective_draft:
        obj_lines.extend(
            [
                "",
                "#### 스태프 입력 초안 (검토 전)",
                objective_draft,
            ]
        )
    obj = "\n".join(obj_lines)
    asm = "\n".join(
        [
            "### 평가 (A)",
            f"- 입력 기반 **비임상** 추정 체질 라벨: **{label}** (출처 메모: {src})",
            "- 상기 라벨은 **병증명·변증명이 아닙니다.** 최종 변증은 한의사가 확정합니다.",
        ]
    )
    plan_lines = [
        "### 계획 (P) — 초안 자리표시",
        "- 처방·침구·구체 처치: **한의사 확정 후 기재**",
        "- 일반적 자가관리 검토(교육용·비지시): 수면 리듬, 자극 식이, 악화 시 내원",
    ]
    if dense:
        plan_lines.extend(
            [
                "",
                "### [Track B] 계획 후보 (가설·비지시)",
                "- 입력 정보만으로 **확정 처치 없음**. 아래는 **판단 재료 후보**(채택·폐기는 원장).",
                "- 증상 군 간 **우선 악화 시나리오**가 있는가? 추가 관찰·검사가 필요한 지점은?",
                "- 기저질환·복약과의 정리: 텍스트-only 한계 명시 후 내원 검사 권유 여부.",
                "- 사상·명리 레이어는 **교육·정리 패킹**으로 유지할지, 환자면에서 제거할지 선택.",
            ]
        )
    pln = "\n".join(plan_lines)
    return {
        "subjective": {"text": subj.strip()},
        "objective": {"text": obj.strip()},
        "assessment": {"text": asm.strip()},
        "plan": {"text": pln.strip()},
    }


def _slot_by_id(bundle: dict[str, Any], sid: str) -> dict[str, Any]:
    for s in bundle.get("patient_slots") or []:
        if s.get("slot_id") == sid:
            return s
    raise KeyError(sid)


SLOT_BODY_MAX = 11800


def _cap_slot_md(text: str, max_len: int = SLOT_BODY_MAX) -> str:
    if len(text) <= max_len:
        return text
    tail = "\n\n…**[잘림]** 스키마 `body_markdown` 상한 초과. 원문 필드는 명리 JSON 원본·`rationale` 참조."
    return text[: max_len - len(tail)] + tail


def _b_track_banner() -> str:
    return "\n".join(
        [
            "> **레일: Track B (연구·가설)** `[HYPO]` 성격. **자동 확정 진단·처방·예후·장기 위험 단정 아님.**",
            "> **역할:** 원장님이 판단할 **정보 밀도 Maximization** 패킷.",
            "> **A-track/본선 임상:** 동일 문서로 **치환·대체 불가**.",
            "",
        ]
    )


def _intake_echo_block(intake_doc: dict[str, Any], max_chars: int = 4500) -> str:
    try:
        blob = json.dumps(intake_doc, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        blob = str(intake_doc)
    if len(blob) > max_chars:
        blob = blob[: max_chars - 40] + '\n  …(JSON 잘림)'
    return "### 인테이크 원본 에코 (감사)\n\n```json\n" + blob + "\n```\n"


PHYSICIAN_ADJ_OPTION_FORKS: list[dict[str, Any]] = [
    {
        "fork_id": "output_density",
        "title_ko": "번호들 밀도 (스크립트 플래그)",
        "role": "원장/운영은 환자면 복잡도에 맞춰 재실행 시 선택할 수 있습니다 (자동 아님).",
        "choices": [
            {
                "choice_id": "dense_default",
                "invoke": "`py scripts/build_patient_intake_fusion_draft_v1.py` … *(기본적으로 `--brief-output` 없음)*",
                "effect": "슬롯에 Track B 밀도 패킷·추가 disclaimer.",
            },
            {
                "choice_id": "brief",
                "invoke": "`--brief-output`",
                "effect": "짧은 구버전 형태 슬롯.",
            },
        ],
    },
    {
        "fork_id": "intake_include_logos",
        "title_ko": "`intake`/인테이크 JSON 안의 상징 축 포함",
        "role": "`options.include_logos_symbolic` 로 끕니다.",
        "choices": [
            {
                "choice_id": "on",
                "invoke": '`options.include_logos_symbolic`: true 또는 생략(기본 true)',
                "effect": "`logos_opt` 슬롯 채움·[NON_GATING] 유지.",
            },
            {
                "choice_id": "off",
                "invoke": "`options.include_logos_symbolic`: false",
                "effect": "`logos_opt` 비포함(empty).",
            },
        ],
    },
    {
        "fork_id": "myeongni_windows",
        "title_ko": "명리 리포트 윈도 길이 (인테이크 `options`)",
        "role": "연·월운 범위 늘리기만 가능; 역법 귀속 해석 금지(원장 책임).",
        "choices": [
            {
                "choice_id": "annual_start_year",
                "invoke": "`options.annual_start_year` 정수 — 기준 연 시작",
                "effect": "`build_myeongni_full_report_v1` 서브실행 재계산.",
            },
            {
                "choice_id": "annual_years",
                "invoke": "`options.annual_years` 정수 · 기본 실행 시 무시되지 않고 리포터에 반영되는 범위",
                "effect": "대운/연별 블록 범위가 달라질 수 있습니다.",
            },
            {
                "choice_id": "monthly_months_per_year",
                "invoke": "`options.monthly_months_per_year` 정수",
                "effect": "월별 패널 깊이(엔진가용 범위에서).",
            },
        ],
    },
    {
        "fork_id": "intake_validation",
        "title_ko": "인테이크 스키마 검증",
        "role": "표준 플로에서는 켭니다; 깨진 임포트 디버깅 시에만 우회 가능.",
        "choices": [
            {
                "choice_id": "strict",
                "invoke": "`--skip-intake-json-schema` 없이 실행 · 스키마 `patient_intake_fusion_draft_input_v1.schema.json`",
                "effect": "입력 무결성 강하게.",
            },
            {
                "choice_id": "skip",
                "invoke": "`--skip-intake-json-schema`",
                "effect": "JSON만 파싱; 스키마 위반 허용(위험).",
            },
        ],
    },
    {
        "fork_id": "post_slot_templates",
        "title_ko": "번들 작성 후 KO 슬롯 템플릿 덮어쓰기",
        "role": "표준 카피·면책 문구 균질화 vs 융합 본문 보존을 선택합니다.",
        "choices": [
            {
                "choice_id": "none",
                "invoke": "`--apply-slot-templates` 없음",
                "effect": "융합 슬롯 유지.",
            },
            {
                "choice_id": "overwrite",
                "invoke": "`--apply-slot-templates` + `scripts/apply_patient_care_bundle_slot_templates_v1.py`",
                "effect": "`patient_care_bundle_slot_templates_ko_v1.json` 기준 채움.",
            },
            {
                "choice_id": "fill_empty_only",
                "invoke": "`--apply-slot-templates` 및 `--apply-slot-templates-fill-empty-only`",
                "effect": "빈 본문만 채우고 기존 융합 분량은 유지하려 할 때 사용.",
            },
        ],
    },
    {
        "fork_id": "policy_and_schema_gate",
        "title_ko": "게이트(번들 작성 직후)",
        "role": "통과해야만 레포 규격에 맞는 환자면 정책을 만족할 수 있습니다.",
        "choices": [
            {
                "choice_id": "policy_validate",
                "invoke": "`--validate-policy` (기본 정책 `patient_care_bundle_generation_policy_v1.default.json`)",
                "effect": "`validate_patient_care_bundle_against_policy_v1` 실행.",
            },
            {
                "choice_id": "bundle_schema",
                "invoke": "`--validate-schema`",
                "effect": "`patient_care_bundle_v1` jsonschema 검증.",
            },
        ],
    },
    {
        "fork_id": "patient_facing_md",
        "title_ko": "단일 파일 MD 렌더",
        "role": "외부 검토 시 한 파일로 넘길 때.",
        "choices": [
            {"choice_id": "render", "invoke": "`--render-md-out <path>`", "effect": "`render_patient_care_bundle_markdown_v1.py` 출력."},
            {"choice_id": "skip", "invoke": "옵션 생략", "effect": "JSON만 제공."},
        ],
    },
    {
        "fork_id": "cds_upstream_assemble",
        "title_ko": "KM CDS 봉투가 따로 있는 경우 조립 레인 (**별 실행**)",
        "role": "`build_patient_intake_fusion_draft_v1`와 합선되지 않는 상류 파이프라인 선택지입니다.",
        "choices": [
            {
                "choice_id": "cds_chain",
                "invoke": "`py scripts/build_patient_care_bundle_from_km_cds_chain_v1.py` 등 (CONSTITUTION §9 참조)",
                "effect": "CDS 검증 후 `assemble_patient_care_bundle_with_myeongni_v1`.",
            },
            {
                "choice_id": "manual_assemble",
                "invoke": "`py scripts/assemble_patient_care_bundle_with_myeongni_v1.py ...` + `--cds-envelope-json`(선택)",
                "effect": "SOAP·번들 단일 조립 분기만.",
            },
            {
                "choice_id": "invoke_assemble_pf",
                "invoke": "`Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1`",
                "effect": "템플릿·정책·렌더를 묶어 환자면 번들 패키지 (Fact-Lock §9).",
            },
        ],
    },
]


def _build_run_option_snapshot(args: argparse.Namespace, intake_doc: dict[str, Any], *, dense: bool) -> dict[str, Any]:
    """이번 명령에 대한 재현 가능 스냅샷 — 자동 판단이 아니라 '요청 상태' 고정."""

    opt = intake_doc.get("options") if isinstance(intake_doc.get("options"), dict) else {}
    logos = True
    if "include_logos_symbolic" in opt:
        logos = bool(opt["include_logos_symbolic"])

    md_path = getattr(args, "render_md_out", None)
    md_repr: Any
    if md_path is None:
        md_repr = None
    else:
        md_repr = str(md_path)

    return {
        "requested_output_density": "dense_b_track_max" if dense else "brief",
        "intake_options_resolved_echo": dict(opt),
        "include_logos_resolved": logos,
        "cli_requested_flags": {
            "brief_output": bool(args.brief_output),
            "skip_intake_json_schema": bool(args.skip_intake_json_schema),
            "validate_bundle_schema_when_done": bool(args.validate_schema),
            "validate_generation_policy_when_done": bool(args.validate_policy),
            "apply_slot_templates_requested": bool(args.apply_slot_templates),
            "apply_slot_templates_fill_empty_only_requested": bool(args.apply_slot_templates_fill_empty_only),
            "render_md_out": md_repr,
        },
        "ordering_note_ko": (
            "번호들 작성 직후 `apply_slot_templates`가 있으면 동일 번들 파일이 재작성되므로, "
            "슬롯 본문의 최종문은 디스크 JSON과 확인하세요. 플래그 기록은 본 객체를 따름."
        ),
    }


def _option_catalog_md(
    forks: list[dict[str, Any]],
    *,
    snapshot: dict[str, Any],
    condensed: bool,
) -> str:
    snap_txt = json.dumps(snapshot, ensure_ascii=False, indent=2)
    if condensed:
        snap_show = snap_txt[:2400] + ("…(잘림)" if len(snap_txt) > 2400 else "")
        lines = [
            "### 운영·렌즈 포크 — 요약 (전체표는 rationale JSON)",
            "",
            "**전부 재실행 선택지**입니다. 시스템이 자동 선택하지 않습니다.",
            *[f"- **{fk.get('fork_id')}**: {fk.get('title_ko')}" for fk in forks[:6]],
            "- `cds_upstream_assemble`: CDS·패킹 조립 — 이 스크립트와 **별 레인**입니다.",
            "",
            "#### 요청 스냅샷(re-run 비교)",
            "```json",
            snap_show,
            "```",
            "",
        ]
        return "\n".join(lines)

    snap_body = snap_txt[:8200] + ("…(잘림, rationale 전체 참조)" if len(snap_txt) > 8200 else "")
    lines = [
        "## 운영·렌즈 포크 — 전체 재현 카탈로그 (원장·운영 결정 메뉴)",
        "",
        "> 라인마다 재실행·덮어쓰기 **선택지**입니다. 진단처방 경로 확정 기능은 없습니다.",
        "",
        "#### 요청 스냅샷 (`rationale.run_option_snapshot_final`)",
        "```json",
        snap_body,
        "```",
        "",
    ]

    for fk in forks:
        fk_id = fk.get("fork_id", "?")
        title = fk.get("title_ko", "")
        role = fk.get("role") or ""
        lines.append(f"### 포크 `{fk_id}` · {title}")
        if role:
            lines.extend(["", role, ""])
        for ch in fk.get("choices") or []:
            cid = ch.get("choice_id", "?")
            inv = ch.get("invoke") or ""
            eff = ch.get("effect") or ""
            lines.append(f"- **`{cid}`** — 실행: {inv}")
            lines.append(f"  - 효과: {eff}")
        lines.append("")
    return "\n".join(lines)


def _physician_adj_checklist(
    symptoms: list[Any], situation: str, sasang_label: str, objective_draft: str
) -> str:
    syms = ", ".join(str(x) for x in symptoms) if symptoms else "—"
    lines = [
        "### 한의사 판단·교차 확인 체크리스트 (정보 패킹)",
        "",
        "- 증상 군(**입력**: "
        + syms
        + ") 중 **증거 기반 우선 순위**(악화·발화기·신경)·**증거 부족** 구간을 어디까지로 둘지.",
        "- **체중 변화**(문맥)·**통증 양상**과 **약물/기저질환**의 인과 가능성 분기(설명만, 단정 회피).",
        "- `situation` 문맥: **" + (situation[:500] + ("…" if len(situation) > 500 else "") if situation else "—") + "**",
        "- 추정 체질 라벨 **" + sasang_label + "** 와 증상의 **변증 학파별 해석 차이**(보류 가능성).",
        "- `objective_draft` 신뢰도·재측정 필요 여부(스태프 입력만 있을 때).",
        "- 객관 초안 미리보기: **" + (objective_draft[:400] + ("…" if len(objective_draft) > 400 else "") if objective_draft else "—") + "**",
        "- 명리 슬롯은 **역법·달력 패턴** 패킷만 — 임신·수술·사망 같은 **예후 단정에 끌어오지 않기.**",
        "- Logos 슬롯은 **환자 교육/가치 프레임** 용도로만 채택할지 결정.",
        "- 환자 전달본에 넣기 전 **core·SOAP** 교정 여부 및 면책 문구 일치 검토.",
        "",
    ]
    return "\n".join(lines)


def _load_clinical_lens_pack() -> dict[str, Any] | None:
    if not CLINICAL_LENS_PACK_JSON.is_file():
        return None
    doc = json.loads(CLINICAL_LENS_PACK_JSON.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "sasang_boming_jiju_clinical_lens_pack_v1":
        return None
    return doc


def _myeongni_sasang_cross_section(report: dict[str, Any], clinical_label: str) -> str:
    if not clinical_label or clinical_label == "미입력":
        return ""
    try:
        from scripts.core.patient_intake_myeongni_sasang_cross_v1 import render_cross_check_markdown

        return render_cross_check_markdown(report, clinical_label).strip()
    except Exception:
        return ""


def _sasang_clinical_lens_pack_section(
    label: str,
    symptom_list: list[Any],
    situation: str,
) -> str:
    try:
        from scripts.core.sasang_boming_jiju_clinical_lens_v1 import render_markdown_section
    except ImportError:
        return ""
    pack = _load_clinical_lens_pack()
    block = render_markdown_section(
        label,
        symptom_list,
        situation,
        pack=pack,
    )
    return "\n\n" + block if block else ""


def _sasang_b_track_hypothesis_pack(
    label: str,
    symptom_list: list[Any],
    situation: str,
) -> str:
    syms = symptom_list if isinstance(symptom_list, list) else []
    rows = []
    for s in syms[:16]:
        rows.append(f"| `{s}` | (B) 입력-only — 변증 교차 검증 필요 | 원장 변증과 일치/불일치 근거? |")
    if not rows:
        rows.append("| *(증상 미입력)* | — | 증상 수집 |")
    hypo_table = (
        "### 증상–추정체질 가설 매핑 (임상 귀속 금지)\n\n"
        "| 증상(입력) | B-track 표기 | 한의사 확인 |\n"
        "|------------|----------------|-------------|\n"
        + "\n".join(rows)
        + "\n"
    )
    extra = (
        "### 가설 분기 (판단 재료)\n\n"
        f"- 입력 추정 라벨 **{label}** 을 채택·폐기·보류할 때 필요한 **진찰/설문 추가 항목**을 나열.\n"
        f"- 배경 컨텍스트: {(situation[:1200] + '…') if len(situation) > 1200 else situation or '—'}\n\n"
        "### 패턴 패킹 (교육/탐색)\n\n"
        "- 족욕·저온 자극·수면 패턴 같은 **저위험 생활 축**을 어느 정도까지 환자교육으로 줄지 선택.\n"
        "- 증상이 **복수 체계**(근골격·내과·신경)에 걸치면 학파 혼선 메모 필드 활용을 권장.\n\n"
    )
    return hypo_table + extra


def _myeongni_dense_appendix(report: dict[str, Any], report_rel: str) -> str:
    pillars = report.get("pillars") or {}
    dm = report.get("day_master") or {}
    sa = report.get("structure_analysis") or {}
    dae = report.get("daewoon") or {}

    dh = sa.get("day_master_strength_hint") or {}
    el = sa.get("element_profile") or {}

    lines: list[str] = [
        "## [HYPO] 명리 엔진 패킹 (판단 재료만)",
        "",
        "**주의:** 일간 세력·오행 카운트는 **엔진 휴리스틱**이며 용신·임상 해석 단정 아님.",
        "",
        "### 사주 원국 (결정론 표면)",
        f"- 년월일시 표기: **{pillars.get('year')}** · **{pillars.get('month')}** · **{pillars.get('day')}** · **{pillars.get('hour')}**",
        f"- 일간 문자: **{dm.get('stem_hangul', '?')}** (`stem_element_hint`: {dm.get('stem_element_hint', '—')})",
        "",
        "### 구조 신호 요약 (엔진 출력)",
        f"- 세력 라벨(휴리스틱): **{dh.get('strength_label', '—')}**",
        f"- 일간 원소(엔진): **{dh.get('day_master_element', '—')}**, 월지 계절 힌트: **{dh.get('season_element_hint', '—')}**",
        f"- 엔진 노트: {dh.get('note', '—')}",
        "",
        "### 간지 간 오행 카운트(표면)",
    ]
    if isinstance(el, dict):
        ecs = el.get("element_counts_visible")
        dom = el.get("dominant_element_visible")
        weak = el.get("weakest_element_visible")
        lines.append(f"- visible counts: `{ecs}`")
        lines.append(f"- dominant_visible: **{dom}** · weakest_visible: **{weak}**")

    cycles = dae.get("cycles") if isinstance(dae, dict) else None
    if isinstance(cycles, list) and cycles:
        lines.extend(["", "### 대운·연령 윤곽 (엔진 사이클; 임상 인과 금지)", "| 대략 나이 구간 | 기둥(엔진) |", "|----------------|------------|"])
        for c in cycles[:10]:
            if not isinstance(c, dict):
                continue
            lines.append(f"| {c.get('age_start')}–{c.get('age_end')} | {c.get('pillar')} |")

    qi = None
    if isinstance(dae, dict) and isinstance(dae.get("qiyun"), dict):
        qi = dae["qiyun"].get("qiyun_years_float") or dae["qiyun"].get("qiyun_days")
    if qi is not None:
        lines.append("")
        lines.append(f"- 기운(엔진 float/days 힌트): `{qi}` (해석은 한의사·역법 전문 범위)")

    lines.extend(
        [
            "",
            "### 구조 분석 JSON 발췌 (원문 일부)",
            "```json",
        ]
    )
    try:
        sa_snip = json.dumps(sa, ensure_ascii=False, indent=2)[:4500]
    except (TypeError, ValueError):
        sa_snip = str(sa)[:4500]
    lines.append(sa_snip)
    lines.extend(["```", "", f"- 전체 리포트: `{report_rel}`"])
    return "\n".join(lines)


def _logos_dense_pack() -> str:
    return "\n".join(
        [
            "[NON_GATING] Logos·상징 축 — **임상 결정 변경 금지.**",
            "",
            "### 스트레스·부하 시 정렬 프레임 (환자 대화용 초안)",
            "- **한 박자 지연**: 즉석 결단 대신 회진·추적 데이터부터.",
            "- **노출 한계**: 업무 책임 노출량 상한 재협상(비의료 카피).",
            "- **회복 우선 순위**: 수면 세그먼트 보전 vs 생산성 레버리 사이에서 환자가 고를 카드 제시만.",
            "",
            "### 패브릭 (은유 선택지)",
            "- “장기 레이스 / 단거리 스퍼트” 비유로 **무리 회복 밀도** 논의(의학 단정 금지).",
            "",
        ]
    )


def _append_dense_disclaimers(bundle: dict[str, Any]) -> None:
    extras = [
        "[Track B·HYPO 패킷] 본 번들 Dense 모드 출력은 정보 제공 목적입니다. 진단명·처방·응급 판단의 자동 근거가 될 수 없습니다.",
        "원장 확정 후에만 환자면으로 전달 가능하며, SaMD·의료규격 범위는 병원 컴플라이언스 절차를 따릅니다.",
    ]
    for e in extras:
        if e not in bundle.get("disclaimers", []):
            bundle.setdefault("disclaimers", []).append(e)


def _enrich_bundle_slots(
    bundle: dict[str, Any],
    intake_doc: dict[str, Any],
    report: dict[str, Any],
    myeongni_rel: str,
    mod: Any,
    *,
    dense: bool,
    catalog_snapshot: dict[str, Any],
) -> None:
    inn = intake_doc.get("intake") or {}
    symptoms = inn.get("symptoms") or []
    situation = str(inn.get("situation") or "").strip()
    objective_draft = str(inn.get("objective_draft") or "").strip()
    se = inn.get("sasang_estimate") or {}
    label = str(se.get("label") or "미입력").strip()
    opt = intake_doc.get("options") or {}
    include_logos = bool(opt.get("include_logos_symbolic", True))

    sym_line = ", ".join(str(x) for x in symptoms) if symptoms else "미기재"

    rationale_common = (
        "## 근거 요약 (출력 절차 — 이론·핵심 IP 비노출)\n\n"
        "| 단계 | 무엇을 썼는가 |\n"
        "|------|----------------|\n"
    )

    if not dense:
        core_body = "\n".join(
            [
                "## 진료 요약 슬롯 (초안)",
                "",
                "이 세션의 **SOAP**는 환자/스태프가 입력한 증상·상황·추정 체질 라벨을 한쪽에 모았습니다. "
                "**최종 의학적 판단·처치는 한의사만** 확정하십시오.",
                "",
                rationale_common
                + "| SOAP | 입력 필드 → `clinical_soap_v1` |\n"
                + "| 특성 | 사상·명리·Logos 슬롯 병치 |\n",
                "",
                f"- **증상(입력):** {sym_line}",
                f"- **상황(입력):** {situation or '—'}",
                f"- **추정 체질 라벨(입력):** {label}",
                "",
                _option_catalog_md(
                    PHYSICIAN_ADJ_OPTION_FORKS,
                    snapshot=catalog_snapshot,
                    condensed=True,
                ),
            ]
        )
        _slot_by_id(bundle, "core")["body_markdown"] = core_body

        lens_brief = _sasang_clinical_lens_pack_section(label, symptoms, situation).strip()
        sasang_brief_parts = [
            f"## 체질·생활 리듬 (추정: **{label}**)",
            "",
            "**임상 변증명 아님.**",
            "",
        ]
        if lens_brief:
            sasang_brief_parts.extend([lens_brief, ""])
        sasang_brief_parts.extend(
            [
                "### 생활 초안 (검토용)",
                "- 수면·각성 리듬, 자극 식이·과로 패턴 점검",
                "",
                rationale_common + "| 사상 | `sasang_estimate` + 증상 맥락 |\n",
                f"- 입력: {sym_line} / {situation or '—'}",
            ]
        )
        sasang_body = "\n".join(sasang_brief_parts)
        sslot = _slot_by_id(bundle, "sasang")
        sslot["included"] = True
        sslot["body_markdown"] = sasang_body

        myeongni_base = mod._myeongni_slot_body(report, myeongni_rel)
        cross_md = _myeongni_sasang_cross_section(report, label)
        myeongni_extra = "\n\n" + rationale_common + "| 명리 | `build_myeongni_full_report_v1` JSON |\n"
        if cross_md:
            myeongni_extra = "\n\n" + cross_md + myeongni_extra
        mslot = _slot_by_id(bundle, "myeongni_ref")
        mslot["body_markdown"] = myeongni_base + myeongni_extra

        logos = _slot_by_id(bundle, "logos_opt")
        logos_ack = logos.get("non_gating_ack") or ""
        if include_logos:
            logos["included"] = True
            logos["body_markdown"] = "\n".join(
                [
                    "[NON_GATING] 가치·우선순위 정렬용 비유.",
                    "",
                    "### 상징 해설 (초안)",
                    "- 스트레스 시 판단 한 박자 나누기·사실 확인부터.",
                    "",
                    logos_ack,
                ]
            )
        else:
            logos["included"] = False
            logos["body_markdown"] = ""
        return

    # --- Track B dense maximum (default) ---
    core_body_dense = "\n".join(
        [
            _b_track_banner(),
            "## 진료 코어 — B-track 정보 밀도 패킷",
            "",
            "**한의사 adjudication** 전용: 환자면 전달 전 core·SOAP 교정.",
            "",
            _intake_echo_block(intake_doc),
            rationale_common
            + "| SOAP | `symptoms`·`situation`·`notes`·`sasang_estimate`·`objective_draft` |\n"
            + "| 병치 | 사상·명리·Logos 슬롯 동세션 |\n",
            "",
            "### 입력 지도 (빠른 색인)",
            f"- 증상: {sym_line}",
            f"- 상황: {situation or '—'}",
            f"- 추정 체질(입력만): **{label}**",
            "",
            _physician_adj_checklist(symptoms, situation, label, objective_draft),
            "",
            _option_catalog_md(
                PHYSICIAN_ADJ_OPTION_FORKS,
                snapshot=catalog_snapshot,
                condensed=False,
            ),
        ]
    )
    _slot_by_id(bundle, "core")["title"] = "진료 코어 · Track B 패킷 (한의사 검토)"
    _slot_by_id(bundle, "core")["body_markdown"] = _cap_slot_md(core_body_dense)

    lens_block = _sasang_clinical_lens_pack_section(label, symptoms, situation).strip()
    sasang_parts = [
        _b_track_banner(),
        f"## 사상 축 — 입력 `{label}` 중심 가설 패킹",
        "",
        "**슬롯 trust_tier 참고:** 스키마상 `clinical_reference`이나, **내용은 전면 B-track·비임상 라벨만** 다룸.",
        "",
    ]
    if lens_block:
        sasang_parts.extend([lens_block, ""])
    cross_sasang = _myeongni_sasang_cross_section(report, label)
    if cross_sasang:
        sasang_parts.extend([cross_sasang, ""])
    sasang_parts.extend(
        [
            _sasang_b_track_hypothesis_pack(label, symptoms, situation),
            rationale_common + "| 사상 | 입력 라벨·증상 목록·상황 블록 |\n",
        ]
    )
    sasang_dense = "\n".join(sasang_parts)
    sslot = _slot_by_id(bundle, "sasang")
    sslot["included"] = True
    sslot["title"] = "사상·체질 추정 [HYPO] 심층 (B-track)"
    sslot["body_markdown"] = _cap_slot_md(sasang_dense)

    myeongni_base = mod._myeongni_slot_body(report, myeongni_rel)
    cross_md = _myeongni_sasang_cross_section(report, label)
    mye_dense_parts = [
        _b_track_banner(),
        myeongni_base,
        "",
    ]
    if cross_md:
        mye_dense_parts.extend([cross_md, ""])
    mye_dense_parts.extend(
        [
            _myeongni_dense_appendix(report, myeongni_rel),
            "",
            rationale_common
            + "| 명리 | 로컬 출생+TZ → `build_myeongni_full_report_v1`; 본문 표·JSON 발췌는 **엔진 표면** |\n"
            + "| 금지 | 임상 장기·예후·처방으로의 **직접 연역** 없음 |\n",
        ]
    )
    mye_dense = "\n".join(mye_dense_parts)
    mslot = _slot_by_id(bundle, "myeongni_ref")
    mslot["title"] = "명리 엔진 패킹 [HYPO] · B-track Max"
    mslot["body_markdown"] = _cap_slot_md(mye_dense)

    logos = _slot_by_id(bundle, "logos_opt")
    logos_ack = logos.get("non_gating_ack") or ""
    if include_logos:
        logos["included"] = True
        logos["title"] = "Logos 프레임 [NON_GATING] · B-track 두껍게"
        logos["body_markdown"] = _cap_slot_md(_logos_dense_pack() + "\n" + logos_ack)
    else:
        logos["included"] = False
        logos["body_markdown"] = ""


def _build_cross_checks_v1(
    intake_doc: dict[str, Any],
    myeongni_report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Structured [HYPO] cross-checks for rationale sidecar (machine-readable)."""
    out: dict[str, Any] = {}
    inn = intake_doc.get("intake") or {}
    se = inn.get("sasang_estimate") or {}
    label = str(se.get("label") or "").strip()
    if myeongni_report and label and label != "미입력":
        try:
            from scripts.core.patient_intake_myeongni_sasang_cross_v1 import assess_myeongni_sasang_cross

            out["myeongni_sasang_clinical_v1"] = assess_myeongni_sasang_cross(myeongni_report, label)
        except Exception as exc:
            out["myeongni_sasang_clinical_v1"] = {
                "status": "insufficient",
                "error": str(exc)[:200],
            }
    if label and CLINICAL_LENS_PACK_JSON.is_file():
        try:
            from scripts.core.sasang_boming_jiju_clinical_lens_v1 import resolve_constitution_id

            pack = json.loads(CLINICAL_LENS_PACK_JSON.read_text(encoding="utf-8-sig"))
            cid = resolve_constitution_id(label)
            if cid and pack.get("schema") == "sasang_boming_jiju_clinical_lens_pack_v1":
                sl = (pack.get("constitutions") or {}).get(cid) or {}
                out["sasang_boming_jiju_lens_v1"] = {
                    "pack_path": _rel_workspace(CLINICAL_LENS_PACK_JSON),
                    "constitution_id": cid,
                    "deep_link_count": len(sl.get("cross_ref_deep_links") or []),
                    "boming_term_count": len(sl.get("boming_jiju_terms") or []),
                    "clinical_question_count": len(sl.get("clinical_priority_questions") or []),
                }
        except Exception:
            pass
    return out


def _build_rationale_sidecar(
    intake_doc: dict[str, Any],
    bundle_path: Path,
    myeongni_path: Path,
    *,
    dense: bool,
    run_snapshot_final: dict[str, Any],
    birth_resolution_v1: dict[str, Any],
    myeongni_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cross_checks = _build_cross_checks_v1(intake_doc, myeongni_report)
    doc: dict[str, Any] = {
        "schema": "patient_intake_fusion_rationale_v1",
        "version": "1.1.0" if cross_checks else "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rail": "Track B",
        "output_density": "dense_b_track_max" if dense else "brief",
        "adjudication_model": "physician_final_authority_non_auto",
        "bundle_out": _rel_workspace(bundle_path),
        "myeongni_full_report": _rel_workspace(myeongni_path),
        "inputs_echo": {
            "profile": intake_doc.get("profile"),
            "intake": intake_doc.get("intake"),
            "encounter": intake_doc.get("encounter"),
            "meta": intake_doc.get("meta"),
        },
        "pipeline": [
            {
                "stage": "soap_draft",
                "sources": ["intake.symptoms", "intake.situation", "intake.subjective_notes", "intake.sasang_estimate"],
                "method": "템플릿 조합 → clinical_soap_v1 (초안); dense 시 Track B 계획 후보 블록 추가",
                "core_theory_disclosure": "none",
            },
            {
                "stage": "myeongni_deterministic",
                "sources": ["profile.birth_instant_utc|profile.local_birth+dst_fold", "profile.iana_tz", "profile.is_male"],
                "method": "saju_birth_resolver_v1 → build_myeongni_full_report_v1 (서브프로세스); dense 시 pillars/structure/daewoon 표면 인용",
                "core_theory_disclosure": "none",
            },
            {
                "stage": "lens_slots",
                "sources": ["intake", "myeongni JSON 경로"],
                "method": "B-track 슬롯 밀도 최대화 또는 brief; 임상 단정 없음",
                "core_theory_disclosure": "none",
            },
        ],
        "physician_adj_option_fork_catalog_v1": PHYSICIAN_ADJ_OPTION_FORKS,
        "run_option_snapshot_final": run_snapshot_final,
        "birth_resolution_v1": birth_resolution_v1,
        "cross_checks_v1": cross_checks,
        "disclaimer": (
            "Track B 연구 레일 패킷. 임상 규제 목적 SaMD/진단 대체 불가. "
            "원장 판단 후 환자 제공. dense=최대 정보·가설 밀도."
            if dense
            else "연구·초안. 짧은 출력 모드 brief-output."
        ),
    }
    return doc


def _run_helper(script: Path, argv: list[str], what: str) -> None:
    cmd = [sys.executable, str(script), *argv]
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if p.returncode != 0:
        msg = (p.stderr or "") + (p.stdout or "")
        print(msg, file=sys.stderr)
        raise SystemExit(f"{what} failed exit {p.returncode}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Intake JSON → SOAP draft + patient_care_bundle_v1 (fusion draft + rationale sidecar)."
    )
    ap.add_argument("--intake-json", type=Path, required=True)
    ap.add_argument(
        "--myeongni-out",
        type=Path,
        default=ROOT / "reports" / "patient_intake_fusion_myeongni_latest.json",
    )
    ap.add_argument(
        "--bundle-out",
        type=Path,
        default=ROOT / "reports" / "patient_intake_fusion_bundle_draft_latest.json",
    )
    ap.add_argument(
        "--rationale-out",
        type=Path,
        default=ROOT / "reports" / "patient_intake_fusion_rationale_latest.json",
    )
    ap.add_argument("--validate-schema", action="store_true")
    ap.add_argument("--validate-policy", action="store_true")
    ap.add_argument("--render-md-out", type=Path, default=None)
    ap.add_argument("--apply-slot-templates", action="store_true", help="Overwrite/fill from KO templates")
    ap.add_argument(
        "--apply-slot-templates-fill-empty-only",
        action="store_true",
        help="With --apply-slot-templates: only fill empty slot bodies (keeps fusion text)",
    )
    ap.add_argument(
        "--skip-intake-json-schema",
        action="store_true",
        help="Skip jsonschema validation of --intake-json against patient_intake_fusion_draft_input_v1",
    )
    ap.add_argument(
        "--brief-output",
        action="store_true",
        help="Short slot bodies (legacy). Default is Track B dense max pack.",
    )
    args = ap.parse_args()

    if not args.intake_json.is_file():
        raise SystemExit(f"missing --intake-json {args.intake_json}")

    raw = json.loads(args.intake_json.read_text(encoding="utf-8-sig"))
    if not args.skip_intake_json_schema:
        if not SCHEMA_INTAKE.is_file():
            raise SystemExit(f"missing intake schema: {SCHEMA_INTAKE}")
        try:
            import jsonschema
        except ImportError as e:
            raise SystemExit("jsonschema required for intake validation (or use --skip-intake-json-schema)") from e
        jsonschema.validate(
            instance=raw,
            schema=json.loads(SCHEMA_INTAKE.read_text(encoding="utf-8")),
        )
    profile = raw.get("profile") or {}
    local_tuple, birth_res_meta = _resolve_birth_engine_tuple(profile)
    iana_tz = str(profile.get("iana_tz") or "Asia/Seoul")
    is_male = bool(profile.get("is_male", False))
    opt = raw.get("options") or {}
    annual_start = int(opt.get("annual_start_year", datetime.now(timezone.utc).year))
    annual_years = int(opt.get("annual_years", 3))
    monthly_m = int(opt.get("monthly_months_per_year", 12))

    mod = _load_assemble()
    report = mod._run_myeongni_report(
        local_tuple,
        iana_tz,
        is_male,
        args.myeongni_out,
        annual_start,
        annual_years,
        monthly_m,
    )
    dense_mode = not args.brief_output
    run_snap = _build_run_option_snapshot(args, raw, dense=dense_mode)
    soap = _soap_from_intake(raw, dense=dense_mode)
    mye_rel = _rel_workspace(args.myeongni_out)
    bundle = mod._build_bundle(
        myeongni_report=report,
        myeongni_rel=mye_rel,
        soap=soap,
        generator_id="build_patient_intake_fusion_draft_v1",
        generator_version="1.0.0",
        opinion_sha256=None,
        cds_envelope_rel=None,
        cds_envelope_sha256=None,
    )
    _enrich_bundle_slots(bundle, raw, report, mye_rel, mod, dense=dense_mode, catalog_snapshot=run_snap)
    if dense_mode:
        _append_dense_disclaimers(bundle)

    enc = raw.get("encounter") or {}
    if isinstance(enc, dict):
        tok = str(enc.get("ref_token") or "").strip()
        if tok:
            bundle.setdefault("provenance", {})["encounter_ref"] = tok[:256]

    args.bundle_out.parent.mkdir(parents=True, exist_ok=True)
    args.bundle_out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.apply_slot_templates:
        ts_argv = [
            "--bundle-in",
            str(args.bundle_out),
            "--bundle-out",
            str(args.bundle_out),
            "--templates-json",
            str(SLOT_TEMPLATES_JSON),
            "--myeongni-json",
            str(args.myeongni_out),
            "--myeongni-report-rel",
            mye_rel,
        ]
        if args.apply_slot_templates_fill_empty_only:
            ts_argv.append("--fill-empty-only")
        _run_helper(APPLY_SLOT_TEMPLATES, ts_argv, "apply_slot_templates")

    policy_json_resolved = DEFAULT_POLICY_JSON
    if args.validate_policy:
        if not policy_json_resolved.is_file():
            raise SystemExit(f"policy json missing: {policy_json_resolved}")
        _run_helper(
            VALIDATE_POLICY,
            ["--bundle-json", str(args.bundle_out), "--policy-json", str(policy_json_resolved)],
            "validate_policy",
        )

    if args.render_md_out is not None:
        _run_helper(
            RENDER_BUNDLE_MD,
            ["--bundle-json", str(args.bundle_out), "--out-md", str(args.render_md_out)],
            "render_markdown",
        )

    bundle_schema_checked_ok: None | bool = None
    if args.validate_schema:
        try:
            import jsonschema
        except ImportError as e:
            raise SystemExit("jsonschema required for --validate-schema") from e
        schema_doc = json.loads(SCHEMA_BUNDLE.read_text(encoding="utf-8"))
        final_bundle_doc = json.loads(args.bundle_out.read_text(encoding="utf-8-sig"))
        jsonschema.validate(instance=final_bundle_doc, schema=schema_doc)
        bundle_schema_checked_ok = True

    snap_fin = dict(run_snap)
    snap_fin["post_execution_completed"] = {
        "slot_templates_ran_this_process": bool(args.apply_slot_templates),
        "generation_policy_validated": bool(args.validate_policy),
        "patient_md_render_requested": args.render_md_out is not None,
        "bundle_json_schema_validated_and_passed_last": bundle_schema_checked_ok,
    }

    rat = _build_rationale_sidecar(
        raw,
        args.bundle_out,
        args.myeongni_out,
        dense=dense_mode,
        run_snapshot_final=snap_fin,
        birth_resolution_v1=birth_res_meta,
        myeongni_report=report,
    )
    args.rationale_out.parent.mkdir(parents=True, exist_ok=True)
    args.rationale_out.write_text(json.dumps(rat, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "bundle_out": str(args.bundle_out),
                "myeongni_out": str(args.myeongni_out),
                "rationale_out": str(args.rationale_out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
