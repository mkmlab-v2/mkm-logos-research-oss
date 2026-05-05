import type { KakaoSurveyPayload } from "@/lib/kakao-intake-contract";

export type ClinicianSoapSeed = {
  subjective: string;
  objective: string[];
  assessment_hypothesis: string[];
  plan_questions: string[];
  patient_facing_summary: string;
};

export function buildSoapSeedFromKakaoSurvey(payload: KakaoSurveyPayload): ClinicianSoapSeed {
  const s = `환자 진술: ${payload.health.chief_complaint} / 기간: ${payload.health.symptom_duration}`;
  const o = [
    `통증부위: ${payload.health.pain_area}`,
    `통증강도(0-10): ${payload.health.pain_scale_0_10}`,
    `수면: ${payload.health.sleep_pattern}`,
    `소화: ${payload.health.digestion_pattern}`,
    payload.health.appetite ? `식욕: ${payload.health.appetite}` : "",
    payload.health.bowel_pattern ? `대변패턴: ${payload.health.bowel_pattern}` : "",
  ].filter(Boolean);

  const a = [
    "사상/체질 가설은 참고 레이어로만 사용하고, 임상 소견 우선으로 재검증",
    "명리·사상·기타 렌즈 간 충돌 시 보수적 해석 우선",
    "응급 레드플래그 존재 시 즉시 일반 흐름 중단 후 응급 안내",
  ];

  const p = [
    "악화/완화 인자(시간대, 식사, 스트레스) 3개 이상 재확인",
    "수면·소화·통증 변동 패턴의 주간 리듬 확인",
    "환자 이해용 설명 문구와 내원 후 추적 포인트 합의",
  ];

  return {
    subjective: s,
    objective: o,
    assessment_hypothesis: a,
    plan_questions: p,
    patient_facing_summary:
      "현재 정보는 진단 확정이 아닌 진료 전 정리입니다. 한의사 진찰을 통해 최종 판단과 치료 방향을 확정합니다.",
  };
}

export function buildClinicianOrchestratorPrompt(seed: ClinicianSoapSeed): string {
  return [
    "Role: clinician_orchestrator",
    "Task: merge multi-lens support signals into a conservative SOAP draft.",
    "Constraints:",
    "- no definitive diagnosis/prescription",
    "- separate fact vs hypothesis",
    "- keep patient-facing summary in plain Korean",
    "",
    "S:",
    seed.subjective,
    "",
    "O:",
    ...seed.objective.map((v) => `- ${v}`),
    "",
    "A(hypothesis):",
    ...seed.assessment_hypothesis.map((v) => `- ${v}`),
    "",
    "P(questions):",
    ...seed.plan_questions.map((v) => `- ${v}`),
  ].join("\n");
}
