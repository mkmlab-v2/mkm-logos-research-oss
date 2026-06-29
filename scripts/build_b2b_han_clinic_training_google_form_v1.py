#!/usr/bin/env python3
"""Charter R5 — B2B 한의원 연수 Google Form schema builder [HYPO][passive corral].

Outputs machine-readable form field spec for manual Google Forms import.
No API publish, no patient CRM hook, no external send without human sign-off.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/b2b_han_clinic_training_google_form_v1.schema.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/b2b_han_clinic_training_google_form_v1_latest.json"
REPORT_OUT = ROOT / "reports/b2b_han_clinic_training_google_form_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_form_spec() -> dict[str, Any]:
    return {
        "schema": "b2b_han_clinic_training_google_form_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "charter_ref": "LENS_UTILIZATION_CHARTER_V1 R5",
        "track_wall": "B_track_research_only",
        "passive_corral": {
            "send_gate": "HOLD",
            "ready_for_external_publish": False,
            "patient_funnel_allowed": False,
            "akom_credential_claim_forbidden": True,
            "auto_crm_hook_forbidden": True,
            "requires_human_signoff_before_form_link": True,
            "certificate_scope_ko": "사설 이수 확인용 — AKOM·보수교육 학점·치료 효능 증명 아님",
        },
        "lens_roles_contract": {
            "sasang": "교육·생활 은유 (단기 강도 설명)",
            "myeongni": "선택 일운 참고 (체질 확정·진단 금지)",
            "logos": "2줄 비게이팅 사이드바 [NON_GATING]",
            "field_note": "Field/regime는 렌즈가 아님 — 본 연수 폼에 매매·실전 트리거 수집 금지",
        },
        "sections": [
            {
                "section_id": "clinic_profile",
                "title_ko": "한의원·수강자 정보",
                "description_ko": "내부 연수 등록용. 환자 식별 정보·주민번호 수집 금지.",
                "fields": [
                    {
                        "field_id": "clinic_name",
                        "label_ko": "한의원(기관)명",
                        "google_forms_type": "SHORT_ANSWER",
                        "required": True,
                    },
                    {
                        "field_id": "region_si_do",
                        "label_ko": "소재지 (시·도)",
                        "google_forms_type": "MULTIPLE_CHOICE",
                        "required": True,
                        "options_ko": [
                            "서울",
                            "경기·인천",
                            "충청",
                            "전라",
                            "경상",
                            "강원·제주",
                            "기타",
                        ],
                    },
                    {
                        "field_id": "attendee_role",
                        "label_ko": "수강자 역할",
                        "google_forms_type": "MULTIPLE_CHOICE",
                        "required": True,
                        "options_ko": ["원장", "부원장·진료부", "침구·생활상담", "행정·기타"],
                    },
                    {
                        "field_id": "contact_email_masked",
                        "label_ko": "연락 이메일 (기관용)",
                        "google_forms_type": "SHORT_ANSWER",
                        "required": True,
                        "help_text_ko": "환자 이메일·개인 연락처 대리 수집 금지",
                    },
                ],
            },
            {
                "section_id": "module_intent",
                "title_ko": "연수 모듈 선택",
                "description_ko": "교육 모듈 의향 조사 — 임상 처방·환자 매칭 아님.",
                "fields": [
                    {
                        "field_id": "modules_requested",
                        "label_ko": "희망 모듈 (복수 선택)",
                        "google_forms_type": "CHECKBOX",
                        "required": True,
                        "options_ko": [
                            "사상 생활 4줄 (교육 은유)",
                            "장-뇌·미생물 교육 프레임 (은유)",
                            "명리 일운 참고 (선택·비진단)",
                            "Logos 2줄 사이드바 (비게이팅)",
                            "해부 도판 통제 평면 소개 (rib55 L0)",
                        ],
                    },
                    {
                        "field_id": "preferred_format",
                        "label_ko": "희망 형식",
                        "google_forms_type": "MULTIPLE_CHOICE",
                        "required": True,
                        "options_ko": ["대면 ½일", "화상 2시간", "자료 패키지만", "미정"],
                    },
                ],
            },
            {
                "section_id": "lens_education_ack",
                "title_ko": "3렌즈 교육 한계 확인",
                "description_ko": "모든 항목 필수 — 승격·실매매·환자 소개 약속 없음.",
                "fields": [
                    {
                        "field_id": "ack_no_trading_signal",
                        "label_ko": "본 연수는 투자·매매 신호가 아님을 이해합니다",
                        "google_forms_type": "CHECKBOX",
                        "required": True,
                        "options_ko": ["동의"],
                        "forbidden_claim_guard": True,
                    },
                    {
                        "field_id": "ack_logos_non_gating",
                        "label_ko": "Logos 축은 [NON_GATING] 교육 사이드바임을 이해합니다",
                        "google_forms_type": "CHECKBOX",
                        "required": True,
                        "options_ko": ["동의"],
                        "forbidden_claim_guard": True,
                    },
                    {
                        "field_id": "ack_no_constitution_diagnosis",
                        "label_ko": "명리·사상 내용으로 환자 체질을 확정하지 않겠습니다",
                        "google_forms_type": "CHECKBOX",
                        "required": True,
                        "options_ko": ["동의"],
                        "forbidden_claim_guard": True,
                    },
                ],
            },
            {
                "section_id": "passive_corral_consent",
                "title_ko": "패시브 가두리 동의",
                "description_ko": "자동 환자 유입·CRM 연동·대외 송출 없음.",
                "fields": [
                    {
                        "field_id": "ack_no_patient_funnel",
                        "label_ko": "연수 수료가 환자 소개·네트워크 가입을 의미하지 않음에 동의",
                        "google_forms_type": "CHECKBOX",
                        "required": True,
                        "options_ko": ["동의"],
                        "forbidden_claim_guard": True,
                    },
                    {
                        "field_id": "ack_private_certificate_only",
                        "label_ko": "수료 확인은 사설 이수용이며 AKOM 학점이 아님을 이해",
                        "google_forms_type": "CHECKBOX",
                        "required": True,
                        "options_ko": ["동의"],
                        "forbidden_claim_guard": True,
                    },
                    {
                        "field_id": "ack_no_treatment_efficacy",
                        "label_ko": "교육 자료가 치료 효능·예후를 보장하지 않음을 이해",
                        "google_forms_type": "CHECKBOX",
                        "required": True,
                        "options_ko": ["동의"],
                        "forbidden_claim_guard": True,
                    },
                ],
            },
            {
                "section_id": "completion_feedback",
                "title_ko": "연수 후 피드백 (선택)",
                "description_ko": "교육 품질 개선용 — 임상 데이터 아님.",
                "fields": [
                    {
                        "field_id": "understanding_scale",
                        "label_ko": "3렌즈 역할 구분 이해도 (1–5)",
                        "google_forms_type": "LINEAR_SCALE",
                        "required": False,
                        "scale_min": 1,
                        "scale_max": 5,
                    },
                    {
                        "field_id": "open_feedback",
                        "label_ko": "개선 제안 (자유)",
                        "google_forms_type": "PARAGRAPH",
                        "required": False,
                        "help_text_ko": "환자 사례·실명 기재 금지",
                    },
                ],
            },
        ],
        "disclaimers_ko": [
            "본 Google Form 스펙은 B-track [HYPO] 연수 등록 초안입니다.",
            "투자자문·매매 지시·치료 효능·AKOM 학점 주장 금지.",
            "Logos = [NON_GATING]; Field는 렌즈가 아닙니다.",
            "외부 링크 게시 전 지휘관·법무 HOLD 해제 필요 (passive_corral).",
        ],
        "google_forms_import_notes": [
            "Google Forms UI에 섹션·질문을 수동 복제 (API 자동 게시 없음).",
            "응답 시트는 내부 Drive만; Zapier/CRM 자동 연동 금지 (passive_corral).",
            "checkbox '동의' 항목은 Google Forms '응답 1개 필수'로 설정.",
        ],
        "operator_lines": [
            "- [MKM-B2B-FORM] Charter R5 passive corral; send_gate=HOLD.",
            "- [MKM-B2B-FORM] patient_funnel=false; AKOM credential forbidden.",
            "- [MKM-B2B-FORM] manual Google Forms import only.",
        ],
    }


def _validate(doc: dict[str, Any]) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:
        raise RuntimeError("jsonschema required; pip install jsonschema") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report-json", type=Path, default=REPORT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    if not SCHEMA_PATH.is_file():
        print(json.dumps({"ok": False, "error": "schema missing"}))
        return 2

    doc = build_form_spec()
    _validate(doc)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"

    if args.stdout_only:
        sys.stdout.write(text)
        return 0

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(text, encoding="utf-8")

    n_fields = sum(len(s.get("fields") or []) for s in doc.get("sections") or [])
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "sections": len(doc.get("sections") or []),
                "fields": n_fields,
                "send_gate": doc["passive_corral"]["send_gate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
