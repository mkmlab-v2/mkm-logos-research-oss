import type { CdssCitationV1, ConsultDraftV1, PatientConsultInputV1, SasangType } from "@/lib/cdss-contract";

type ManseryeokResult = { saju_label: string; source: "live" | "fallback" };

const FALLBACK_SAJU: ManseryeokResult = {
  saju_label: "만세력 참조값 미연동(로컬 fallback)",
  source: "fallback",
};

const CANON_CITATION_MAP: Record<SasangType, CdssCitationV1> = {
  taeyang: {
    citation_id: "canon_taeyang_001",
    source_title: "동의수세보원 · 태양인 편",
    source_excerpt: "태양인의 병증은 발산과 수렴의 균형이 깨질 때 악화되기 쉬우므로, 변증 전 생활 리듬을 먼저 살핀다.",
    source_ref: "canon://donguisusebowon/taeyang/section-1",
    evidence_level: "B",
  },
  taeeum: {
    citation_id: "canon_taeeum_001",
    source_title: "동의수세보원 · 태음인 편",
    source_excerpt: "태음인의 식적·울체 경향은 소화와 수면 변화를 함께 보며, 과로·정서 자극 요인을 병행 확인한다.",
    source_ref: "canon://donguisusebowon/taeeum/section-1",
    evidence_level: "A",
  },
  soyag: {
    citation_id: "canon_soyag_001",
    source_title: "동의수세보원 · 소양인 편",
    source_excerpt: "소양인의 상열감과 흉격 불편은 수면·스트레스 반응과 연동되는 경우가 많아 문진 단계에서 교차 확인한다.",
    source_ref: "canon://donguisusebowon/soyag/section-1",
    evidence_level: "A",
  },
  soeum: {
    citation_id: "canon_soeum_001",
    source_title: "동의수세보원 · 소음인 편",
    source_excerpt: "소음인의 한증·허약 경향은 소화력과 활력 저하가 동반되기 쉬우므로, 복약 및 생활 패턴을 함께 본다.",
    source_ref: "canon://donguisusebowon/soeum/section-1",
    evidence_level: "A",
  },
  unknown: {
    citation_id: "guide_clinical_intake_001",
    source_title: "한의 임상 문진 표준 가이드",
    source_excerpt: "체질 정보가 불확실한 경우에도 주증상·발현시점·중증도·복약력·레드플래그를 우선 구조화한다.",
    source_ref: "guide://hanui/intake/v1",
    evidence_level: "B",
  },
};

function pickSasangCandidate(input: PatientConsultInputV1): SasangType {
  const survey = input.lane_a_profile.constitution_survey;
  const heat = (survey.body_heat_preference || "").toLowerCase();
  const digestion = (survey.digestion_pattern || "").toLowerCase();
  const sleep = (survey.sleep_pattern || "").toLowerCase();
  if (heat.includes("열") || heat.includes("hot")) return "soyag";
  if (digestion.includes("더부룩") || digestion.includes("stagnant")) return "taeeum";
  if (sleep.includes("얕") || sleep.includes("light")) return "soeum";
  return "unknown";
}

async function fetchManseryeokReference(birthDatetime: string): Promise<ManseryeokResult> {
  const endpoint = process.env.ATHENA_MANSERYEOK_API_URL?.trim();
  if (!endpoint) return FALLBACK_SAJU;
  const token = process.env.ATHENA_MANSERYEOK_API_TOKEN?.trim();
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "x-api-token": token } : {}),
      },
      body: JSON.stringify({ birth_datetime: birthDatetime }),
    });
    if (!res.ok) return FALLBACK_SAJU;
    const data = (await res.json()) as { saju_label?: string };
    if (typeof data.saju_label !== "string" || data.saju_label.trim().length === 0) return FALLBACK_SAJU;
    return { saju_label: data.saju_label.trim(), source: "live" };
  } catch {
    return FALLBACK_SAJU;
  }
}

export async function buildAdvancedConsultDraft(input: PatientConsultInputV1): Promise<ConsultDraftV1> {
  const saju = await fetchManseryeokReference(input.lane_a_profile.birth_datetime);
  const sasang = pickSasangCandidate(input);
  const citation = CANON_CITATION_MAP[sasang];
  return {
    schema: "consult_draft_v1",
    request_id: input.request_id,
    mode: "cdss_draft",
    profile_summary: { sasang_candidate: sasang, saju_reference: saju.saju_label, saju_source: saju.source },
    clinical_summary: [
      `주증상: ${input.lane_b_clinical.chief_complaint}`,
      `발현: ${input.lane_b_clinical.onset}`,
      `중증도: ${input.lane_b_clinical.severity}`,
      `복약: ${input.lane_b_clinical.medication || "미기재"}`,
    ].join(" / "),
    reasoning: {
      syndrome_hypothesis: "체질 참고 정보(A 레인)와 임상 증상(B 레인)을 분리 해석한 예비 병증 가설입니다.",
      care_direction: "문진 확장 후 변증을 정교화하고, 처방군은 한의사가 최종 선택합니다.",
      caution: "응급·중증 신호 또는 약물 충돌 우려가 있으면 즉시 대면 진료를 우선 적용합니다.",
    },
    citations: [citation],
    requires_physician_confirmation: true,
    non_medical_notice: "본 결과는 진료 보조 초안이며, 최종 진단·처방 판단은 한의사가 직접 확정해야 합니다.",
  };
}
