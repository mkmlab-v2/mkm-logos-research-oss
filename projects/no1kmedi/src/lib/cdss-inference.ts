import type {
  CdssCitationV1,
  CdssGenerationReason,
  ConsultDraftV1,
  PatientConsultInputV1,
  SasangType,
} from "@/lib/cdss-contract";
import { looksLikeIsoInstant } from "@/lib/global-birth-input";

type ManseryeokResult = { saju_label: string; source: "live" | "fallback" };
type LlmReasoning = {
  clinical_summary: string;
  syndrome_hypothesis: string;
  care_direction: string;
  caution: string;
};

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

function isComplexCase(input: PatientConsultInputV1): boolean {
  const complaint = input.lane_b_clinical.chief_complaint || "";
  const medication = input.lane_b_clinical.medication || "";
  const redFlag = input.lane_b_clinical.health_survey?.red_flag_notes || "";
  const mergedLength = `${complaint} ${medication} ${redFlag}`.length;
  return mergedLength > 180 || medication.length > 40 || redFlag.length > 20;
}

function safeJsonParse(text: string): Record<string, unknown> | null {
  try {
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** Dedicated CDSS endpoint, OpenRouter, or Gemini(OpenAI-compatible) in that order. */
function resolveCdssOpenAiCredentials(): { apiBase: string; apiKey: string } | null {
  const dedicatedBase = process.env.CDSS_LLM_API_BASE_URL?.trim();
  const dedicatedKey = process.env.CDSS_LLM_API_KEY?.trim();
  if (dedicatedBase && dedicatedKey) {
    return { apiBase: dedicatedBase.replace(/\/$/, ""), apiKey: dedicatedKey };
  }
  const geminiKey = process.env.GEMINI_API_KEY?.trim() || process.env.GOOGLE_API_KEY?.trim();
  const useGemini = (process.env.CDSS_LLM_USE_GEMINI || "").toLowerCase() === "true";
  if (geminiKey && (useGemini || (process.env.CDSS_LLM_USE_OPENROUTER || "").toLowerCase() !== "true")) {
    return {
      apiBase: "https://generativelanguage.googleapis.com/v1beta/openai",
      apiKey: geminiKey,
    };
  }
  const useOpenRouter = (process.env.CDSS_LLM_USE_OPENROUTER || "").toLowerCase() === "true";
  if (!useOpenRouter) return null;
  const orKey = process.env.OPENROUTER_API_KEY?.trim();
  if (!orKey) return null;
  const orBase = (process.env.OPENROUTER_BASE_URL?.trim() || "https://openrouter.ai/api/v1").replace(/\/$/, "");
  return { apiBase: orBase, apiKey: orKey };
}

function validateLlmReasoning(value: Record<string, unknown> | null): LlmReasoning | null {
  if (!value) return null;
  const clinicalSummary = value.clinical_summary;
  const syndromeHypothesis = value.syndrome_hypothesis;
  const careDirection = value.care_direction;
  const caution = value.caution;
  if (
    typeof clinicalSummary !== "string" ||
    typeof syndromeHypothesis !== "string" ||
    typeof careDirection !== "string" ||
    typeof caution !== "string"
  ) {
    return null;
  }
  if (!clinicalSummary.trim() || !syndromeHypothesis.trim() || !careDirection.trim() || !caution.trim()) return null;
  return {
    clinical_summary: clinicalSummary.trim(),
    syndrome_hypothesis: syndromeHypothesis.trim(),
    care_direction: careDirection.trim(),
    caution: caution.trim(),
  };
}

async function callOpenAiCompatibleModel(model: string, input: PatientConsultInputV1): Promise<LlmReasoning | null> {
  const creds = resolveCdssOpenAiCredentials();
  const timeoutMs = Number(process.env.CDSS_LLM_TIMEOUT_MS || 12000);
  if (!creds || !model) return null;
  const apiBase = creds.apiBase;
  const apiKey = creds.apiKey;

  const systemPrompt = [
    "너는 한의사 진료보조 CDSS 초안을 생성하는 어시스턴트다.",
    "최종 진단/처방을 단정하지 말고, 예비 가설 중심으로 작성한다.",
    "출력은 반드시 JSON만 반환하고, 아래 키를 모두 포함한다:",
    "clinical_summary, syndrome_hypothesis, care_direction, caution",
  ].join(" ");

  const userPrompt = JSON.stringify(
    {
      lane_a_profile: input.lane_a_profile,
      lane_b_clinical: input.lane_b_clinical,
      output_contract: {
        clinical_summary: "string",
        syndrome_hypothesis: "string",
        care_direction: "string",
        caution: "string",
      },
    },
    null,
    2,
  );

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    };
    if (apiBase.includes("openrouter.ai")) {
      headers["HTTP-Referer"] = process.env.OPENROUTER_HTTP_REFERER?.trim() || "https://jema-ai.com";
      headers["X-Title"] = process.env.OPENROUTER_APP_NAME?.trim() || "jema-ai.com CDSS";
    }

    const res = await fetch(`${apiBase.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers,
      signal: controller.signal,
      body: JSON.stringify({
        model,
        temperature: 0.2,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
      }),
    });
    if (!res.ok) {
      console.warn(`[cdss] chat/completions HTTP ${res.status} (model=${model})`);
      return null;
    }
    const payload = (await res.json()) as { choices?: Array<{ message?: { content?: string } }> };
    const content = payload.choices?.[0]?.message?.content;
    if (typeof content !== "string" || !content.trim()) return null;
    return validateLlmReasoning(safeJsonParse(content));
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

type ReasoningRouterOutcome =
  | { ok: true; reasoning: LlmReasoning }
  | { ok: false; reason: CdssGenerationReason };

async function generateReasoningWithRouter(input: PatientConsultInputV1): Promise<ReasoningRouterOutcome> {
  const primaryModel =
    process.env.CDSS_LLM_PRIMARY_MODEL?.trim() ||
    process.env.CDSS_GEMINI_MODEL?.trim() ||
    process.env.GEMINI_MODEL?.trim() ||
    process.env.OPENROUTER_MODEL?.trim() ||
    "";
  const fallbackModel = process.env.CDSS_LLM_FALLBACK_MODEL?.trim() || "";
  const escalationModel = process.env.CDSS_LLM_ESCALATION_MODEL?.trim() || "";
  const enabled = (process.env.CDSS_LLM_ENABLED || "false").toLowerCase() === "true";
  if (!enabled) return { ok: false, reason: "disabled" };

  if (!resolveCdssOpenAiCredentials()) {
    return { ok: false, reason: "no_credentials" };
  }

  let attempted = false;

  if (isComplexCase(input) && escalationModel) {
    attempted = true;
    const escalated = await callOpenAiCompatibleModel(escalationModel, input);
    if (escalated) return { ok: true, reasoning: escalated };
  }

  if (primaryModel) {
    attempted = true;
    const primary = await callOpenAiCompatibleModel(primaryModel, input);
    if (primary) return { ok: true, reasoning: primary };
  }

  if (fallbackModel) {
    attempted = true;
    const fallback = await callOpenAiCompatibleModel(fallbackModel, input);
    if (fallback) return { ok: true, reasoning: fallback };
  }

  if (!attempted) return { ok: false, reason: "no_models" };

  console.warn("[cdss] all configured CDSS model calls failed or returned invalid JSON (network, timeout, or response_format)");
  return { ok: false, reason: "llm_error" };
}

async function fetchManseryeokReference(profile: PatientConsultInputV1["lane_a_profile"]): Promise<ManseryeokResult> {
  const endpoint = process.env.ATHENA_MANSERYEOK_API_URL?.trim();
  if (!endpoint) return FALLBACK_SAJU;
  const token = process.env.ATHENA_MANSERYEOK_API_TOKEN?.trim();
  const utc = profile.birth_instant_utc?.trim();
  const tz = profile.iana_tz?.trim();
  const legacy = profile.birth_datetime?.trim();
  const payload: Record<string, string> = {};
  if (utc && tz && looksLikeIsoInstant(utc)) {
    payload.birth_instant_utc = utc;
    payload.iana_tz = tz;
    if (legacy) payload.birth_datetime = legacy;
  } else if (legacy) {
    payload.birth_datetime = legacy;
  } else {
    return FALLBACK_SAJU;
  }
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "x-api-token": token } : {}),
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return FALLBACK_SAJU;
    const data = (await res.json()) as { saju_label?: string };
    if (typeof data.saju_label !== "string" || data.saju_label.trim().length === 0) return FALLBACK_SAJU;
    return { saju_label: data.saju_label.trim(), source: "live" };
  } catch {
    return FALLBACK_SAJU;
  }
}

function buildFallbackDraftParts(input: PatientConsultInputV1): {
  clinicalSummary: string;
  syndromeHypothesis: string;
  careDirection: string;
  caution: string;
} {
  const complaint = input.lane_b_clinical.chief_complaint || "";
  const sleepPattern = input.lane_a_profile.constitution_survey?.sleep_pattern || "";
  const digestionPattern = input.lane_a_profile.constitution_survey?.digestion_pattern || "";
  const lowerMerged = `${complaint} ${sleepPattern} ${digestionPattern}`.toLowerCase();
  const isFatigueSleepCase =
    lowerMerged.includes("피로") ||
    lowerMerged.includes("fatigue") ||
    lowerMerged.includes("수면") ||
    lowerMerged.includes("sleep");

  if (isFatigueSleepCase) {
    return {
      clinicalSummary: [
        `주증상: ${input.lane_b_clinical.chief_complaint}`,
        `수면 패턴: ${sleepPattern || "미기재"}`,
        `소화 패턴: ${digestionPattern || "미기재"}`,
        "피로-수면-생활리듬 연동 양상을 중심으로 의료진 상담 전 문진 확장 포인트를 정리합니다.",
      ].join(" / "),
      syndromeHypothesis: "피로와 수면 질 저하가 생활 리듬 및 스트레스 반응과 맞물린 예비 병증 가설입니다.",
      careDirection: "생활 리듬 조정, 수면 위생, 복약 이력 재확인을 포함한 상담 검토 순서로 진료 준비를 권장합니다.",
      caution: "증상 급격 악화, 흉통·호흡곤란 등 응급 신호가 있으면 즉시 응급 평가를 우선하고 의료진 대면 진료를 적용합니다.",
    };
  }

  return {
    clinicalSummary: [
      `주증상: ${input.lane_b_clinical.chief_complaint}`,
      `발현: ${input.lane_b_clinical.onset}`,
      `중증도: ${input.lane_b_clinical.severity}`,
      `복약: ${input.lane_b_clinical.medication || "미기재"}`,
    ].join(" / "),
    syndromeHypothesis: "체질 참고 정보(A 레인)와 임상 증상(B 레인)을 분리 해석한 예비 병증 가설입니다.",
    careDirection: "문진 확장 후 변증을 정교화하고, 처방군은 한의사가 최종 선택합니다.",
    caution: "응급·중증 신호 또는 약물 충돌 우려가 있으면 즉시 대면 진료를 우선 적용합니다.",
  };
}

export async function buildAdvancedConsultDraft(input: PatientConsultInputV1): Promise<ConsultDraftV1> {
  const saju = await fetchManseryeokReference(input.lane_a_profile);
  const sasang = pickSasangCandidate(input);
  const citation = CANON_CITATION_MAP[sasang];
  const outcome = await generateReasoningWithRouter(input);
  const llmReasoning = outcome.ok ? outcome.reasoning : null;
  const fallback = buildFallbackDraftParts(input);

  const generation: ConsultDraftV1["generation"] = outcome.ok
    ? { llm_used: true }
    : { llm_used: false, reason: outcome.reason };

  return {
    schema: "consult_draft_v1",
    request_id: input.request_id,
    mode: "cdss_draft",
    profile_summary: { sasang_candidate: sasang, saju_reference: saju.saju_label, saju_source: saju.source },
    clinical_summary: llmReasoning?.clinical_summary || fallback.clinicalSummary,
    reasoning: {
      syndrome_hypothesis: llmReasoning?.syndrome_hypothesis || fallback.syndromeHypothesis,
      care_direction: llmReasoning?.care_direction || fallback.careDirection,
      caution: llmReasoning?.caution || fallback.caution,
    },
    citations: [citation],
    requires_physician_confirmation: true,
    non_medical_notice: "본 결과는 진료 보조 초안이며, 최종 진단·처방 판단은 한의사가 직접 확정해야 합니다.",
    generation,
  };
}
