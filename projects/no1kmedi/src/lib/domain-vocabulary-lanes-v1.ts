/**
 * Domain vocabulary lanes — physician_gold (사상·한의) vs consumer (융합·아키타입).
 * SSOT: docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json
 */

export const DOMAIN_VOCABULARY_LANES_V1 = {
  physician_gold: {
    lane_id: "physician_gold" as const,
    surfaces: ["no1kmedi.com", "clinic.no1kmedi.com", "app.jema-ai.com/clinician"],
    constitution_terms: ["태음인", "소양인", "태양인", "소음인"],
    constitution_codes: ["taeeum", "soyang", "taeyang", "soeum"] as const,
    disclaimer_ko:
      "본 화면은 한의사 진료 보조·사전 문진 정리용입니다. AI 출력은 참고이며 최종 변증·처방은 면허 한의사가 확정합니다.",
  },
  consumer_survey_only: {
    lane_id: "consumer_survey_only" as const,
    surfaces: ["mkmlife.com", "personadiary.com", "jema-ai.com/consumer"],
    archetype_label_ko: "생활 패턴·아키타입 참고",
    forbidden_on_surface: ["태음인 진단", "한의학적 진단", "처방", "MBTI® 공식 검사"],
    disclaimer_ko:
      "웰니스·자가 체크 참고용이며 의료 진단·치료를 대체하지 않습니다. 불편 시 의료기관을 방문하십시오.",
  },
} as const;

export type DomainVocabularyLaneId = keyof typeof DOMAIN_VOCABULARY_LANES_V1;
