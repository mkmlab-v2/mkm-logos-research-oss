import { CORE_CONSTITUTION_QUESTION_IDS, type ConstitutionQuestionId } from "@/lib/constitution-survey-schema";

export const KAKAO_INTAKE_SCHEMA_VERSION = "kakao_intake_v1";

export type KakaoSurveyPayload = {
  schema_version: "kakao_intake_v1";
  channel: "kakao";
  submitted_at_utc?: string;
  patient: {
    name: string;
    phone: string;
    age_band: string;
    sex?: "male" | "female" | "other" | "unknown";
  };
  health: {
    chief_complaint: string;
    pain_area: string;
    pain_scale_0_10: number;
    symptom_duration: string;
    sleep_pattern: string;
    digestion_pattern: string;
    appetite?: string;
    bowel_pattern?: string;
    stress_reactivity?: string;
    red_flags?: {
      chestPain?: boolean;
      breathingTrouble?: boolean;
      paralysisOrSpeech?: boolean;
      highFeverOrBleeding?: boolean;
    };
  };
  constitution: {
    questionnaire_answers: Partial<Record<ConstitutionQuestionId, "a" | "b" | "">>;
    free_text?: string;
  };
  clinic_preference?: {
    region?: string;
    specialty?: string;
    preferred_time?: string;
  };
  consent: {
    privacy: boolean;
    medical: boolean;
  };
};

export type KakaoSurveyValidationResult = {
  ok: boolean;
  error?: string;
  constitution_core_answered_count: number;
};

function isNonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export function normalizePhoneDigits(value: string): string {
  return value.replace(/\D/g, "");
}

export function validateKakaoSurveyPayload(payload: KakaoSurveyPayload): KakaoSurveyValidationResult {
  if (payload.schema_version !== KAKAO_INTAKE_SCHEMA_VERSION) {
    return { ok: false, error: "schema_version_invalid", constitution_core_answered_count: 0 };
  }
  if (payload.channel !== "kakao") {
    return { ok: false, error: "channel_invalid", constitution_core_answered_count: 0 };
  }
  if (!isNonEmpty(payload.patient?.name)) return { ok: false, error: "patient_name_required", constitution_core_answered_count: 0 };
  if (!isNonEmpty(payload.patient?.phone)) return { ok: false, error: "patient_phone_required", constitution_core_answered_count: 0 };
  if (!isNonEmpty(payload.patient?.age_band)) return { ok: false, error: "patient_age_band_required", constitution_core_answered_count: 0 };

  if (!isNonEmpty(payload.health?.chief_complaint)) return { ok: false, error: "chief_complaint_required", constitution_core_answered_count: 0 };
  if (!isNonEmpty(payload.health?.pain_area)) return { ok: false, error: "pain_area_required", constitution_core_answered_count: 0 };
  if (!Number.isFinite(payload.health?.pain_scale_0_10) || payload.health.pain_scale_0_10 < 0 || payload.health.pain_scale_0_10 > 10) {
    return { ok: false, error: "pain_scale_invalid", constitution_core_answered_count: 0 };
  }
  if (!isNonEmpty(payload.health?.symptom_duration)) return { ok: false, error: "symptom_duration_required", constitution_core_answered_count: 0 };
  if (!isNonEmpty(payload.health?.sleep_pattern)) return { ok: false, error: "sleep_pattern_required", constitution_core_answered_count: 0 };
  if (!isNonEmpty(payload.health?.digestion_pattern)) return { ok: false, error: "digestion_pattern_required", constitution_core_answered_count: 0 };

  if (!payload.consent?.privacy || !payload.consent?.medical) {
    return { ok: false, error: "consent_required", constitution_core_answered_count: 0 };
  }

  const qa = payload.constitution?.questionnaire_answers || {};
  const coreAnswered = CORE_CONSTITUTION_QUESTION_IDS.filter((id) => qa[id] === "a" || qa[id] === "b").length;
  if (coreAnswered < 3) {
    return { ok: false, error: "constitution_minimum_core_answers_required", constitution_core_answered_count: coreAnswered };
  }
  return { ok: true, constitution_core_answered_count: coreAnswered };
}
