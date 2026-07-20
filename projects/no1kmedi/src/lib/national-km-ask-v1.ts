/** National KM ask surface copy + keys — canonical host jema-ai.com/ask (Phase 1). */

export const NATIONAL_KM_ASK_V1 = {
  schema: "no1kmedi_national_km_ask_v1",
  version: "0.2.0",
  branding_spec_ref: "docs/final/artifacts/jema_public_branding_spec_v1_latest.json",
  surface_split_ref: "docs/final/artifacts/no1kmedi_ask_vs_clinician_surface_split_v1_latest.json",
  product_name_ko: "한의학, 묻다",
  brand_name_ko: "JEMA 한의학",
  brand_display_en: "J.E.M.A. K-Medi",
  brand_expansion_en: "Je-ma Embodied Metacognitive Architecture",
  brand_expansion_ko: "이제마 체화·메타인지 아키텍처",
  brand_expansion_placement: "footnote_only",
  tagline_ko: "몸과 생활의 한의학 이야기",
  layer_badge_ko: "L0 · 교육·참고 · 진단·처방 대체 아님",
  layer_hint_ko: "Time-to-Trust - 공개 교육 Q&A만. 원장 SOAP·CDSS와 합선하지 않습니다.",
  assistant_role_ko: "한의학 안내",
  empty_lead_ko: "몸과 생활에 대해 한의학적으로 궁금한 것을 물어보세요.",
  empty_hint_ko: "아래 예시 칩으로 시작할 수 있습니다. 답변은 교육·참고용이며 진료·처방이 아닙니다.",
  disclaimer_ko:
    "본 답변은 한의학 이해·생활관리 참고용(L0 교육)이며, 진단·처방·응급 판단을 대체하지 않습니다. 증상이 심하거나 급격히 악화되면 즉시 의료기관을 이용해 주세요.",
  regulatory_disclaimer_ko:
    "본 아키텍처는 진단이나 처방을 대체하지 않는 비임상·교육·성찰 보조 소프트웨어입니다.",
  embodied_pipeline_status: "stub_research_only",
  meta_description_ko:
    "JEMA Korean Medicine · 대국민 한의학 교육·참고 Q&A (L0). 진단·처방·응급 판단 대체 아님. 한의사 SOAP 워크스페이스는 app.jema-ai.com/clinician (현장 북마크 clinic.no1kmedi.com).",
  clinician_footer_preface_ko: "원장이신가요?",
  clinician_footer_cta_ko: "원장 전용 포털",
  clinician_footer_note_ko: "SOAP·진료 보조 워크스페이스 · 공개 Q&A와 분리",
  clinician_official_url: "https://app.jema-ai.com/clinician",
  clinician_field_bookmark_url: "https://clinic.no1kmedi.com/clinician",
  provenance_hold_reason_ko: "원전 자동 cite 미연결 · 가짜 인용 금지 (HOLD)",
} as const;

export const NATIONAL_KM_ASK_STORAGE_KEY = "mkm_national_km_ask_turns_v1";
export const NATIONAL_KM_ASK_DISCLAIMER_KEY = "mkm_national_km_ask_disclaimer_ack_v1";

export const NATIONAL_KM_STARTER_PROMPTS = [
  "소화가 자주 안 좋을 때 한의학에서는 어떻게 봐요?",
  "불면과 피로가 같이 있을 때 생활에서 조절할 점은?",
  "한약은 누구에게 맞나요? 일반인이 알아야 할 주의점은?",
  "어깨·허리 통증을 한의학적으로 이해하려면?",
] as const;
