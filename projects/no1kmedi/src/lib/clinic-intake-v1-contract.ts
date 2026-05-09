export const CLINIC_INTAKE_V1_SCHEMA = "clinic_intake_v1";

export type ClinicIntakeV1Payload = {
  schema_version: "clinic_intake_v1";
  patient: {
    name: string;
    phone: string;
    birthdate: string;
    visit_type: "초진" | "재진";
  };
  consent: {
    sensitive_collection: boolean;
    kakao_transfer: boolean;
    non_diagnostic_notice: boolean;
  };
  red_flags: {
    chestPain: boolean;
    neuroDeficit: boolean;
    highFever: boolean;
    pregnancyOrMajorCondition: boolean;
  };
  symptom: {
    main_symptom: string;
    duration: string;
    severity_nrs: number;
    free_text?: string;
  };
  health_core: {
    sleep_quality: string;
    bowel_pattern: string;
    appetite: string;
    stress_level: number;
    medications?: string;
  };
  constitution: {
    body_frame: string;
    heat_cold_sensitivity: string;
    temperament: string;
    digestion_pattern: string;
    fatigue_recovery: string;
  };
  optional_profile?: {
    birth_time_known?: boolean;
    birth_time?: string;
    chrono_type?: string;
  };
  clinic_preference?: {
    region?: string;
    specialty?: string;
    preferred_time?: string;
  };
  submitted_at_utc?: string;
};

export type ClinicIntakeValidationResult =
  | { ok: true }
  | { ok: false; error: string };

export function normalizePhoneDigits(value: string): string {
  return value.replace(/\D/g, "");
}

function isNonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isValidNrs(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 10;
}

export function validateClinicIntakeV1(payload: ClinicIntakeV1Payload): ClinicIntakeValidationResult {
  if (payload.schema_version !== CLINIC_INTAKE_V1_SCHEMA) {
    return { ok: false, error: "schema_version_invalid" };
  }
  if (!isNonEmpty(payload.patient?.name)) return { ok: false, error: "patient_name_required" };
  if (!isNonEmpty(payload.patient?.phone)) return { ok: false, error: "patient_phone_required" };
  if (!isNonEmpty(payload.patient?.birthdate)) return { ok: false, error: "patient_birthdate_required" };
  if (!isNonEmpty(payload.patient?.visit_type)) return { ok: false, error: "visit_type_required" };

  if (!payload.consent?.sensitive_collection) return { ok: false, error: "consent_sensitive_required" };
  if (!payload.consent?.kakao_transfer) return { ok: false, error: "consent_kakao_required" };
  if (!payload.consent?.non_diagnostic_notice) return { ok: false, error: "consent_notice_required" };

  if (!isNonEmpty(payload.symptom?.main_symptom)) return { ok: false, error: "main_symptom_required" };
  if (!isNonEmpty(payload.symptom?.duration)) return { ok: false, error: "duration_required" };
  if (!isValidNrs(payload.symptom?.severity_nrs)) return { ok: false, error: "severity_nrs_invalid" };

  if (!isNonEmpty(payload.health_core?.sleep_quality)) return { ok: false, error: "sleep_quality_required" };
  if (!isNonEmpty(payload.health_core?.bowel_pattern)) return { ok: false, error: "bowel_pattern_required" };
  if (!isNonEmpty(payload.health_core?.appetite)) return { ok: false, error: "appetite_required" };
  if (!isValidNrs(payload.health_core?.stress_level)) return { ok: false, error: "stress_level_invalid" };

  if (!isNonEmpty(payload.constitution?.body_frame)) return { ok: false, error: "constitution_body_frame_required" };
  if (!isNonEmpty(payload.constitution?.heat_cold_sensitivity)) return { ok: false, error: "constitution_heat_cold_required" };
  if (!isNonEmpty(payload.constitution?.temperament)) return { ok: false, error: "constitution_temperament_required" };
  if (!isNonEmpty(payload.constitution?.digestion_pattern)) return { ok: false, error: "constitution_digestion_required" };
  if (!isNonEmpty(payload.constitution?.fatigue_recovery)) return { ok: false, error: "constitution_fatigue_required" };

  return { ok: true };
}

export function computeClinicTriageLevel(payload: ClinicIntakeV1Payload): "routine" | "priority" | "emergency" {
  const emergency = Boolean(
    payload.red_flags.chestPain ||
      payload.red_flags.neuroDeficit ||
      payload.red_flags.highFever ||
      payload.red_flags.pregnancyOrMajorCondition,
  );
  if (emergency) return "emergency";
  if (payload.symptom.severity_nrs >= 8) return "priority";
  return "routine";
}

export function buildKakaoSummary(payload: ClinicIntakeV1Payload, receiptId: string, triageLevel: "routine" | "priority" | "emergency") {
  const maskedPhone = normalizePhoneDigits(payload.patient.phone);
  const masked =
    maskedPhone.length >= 8
      ? `${maskedPhone.slice(0, 3)}-${maskedPhone.slice(3, 5)}**-${maskedPhone.slice(-2)}**`
      : "masked";

  return {
    message_type: "clinic_intake_summary",
    receipt_id: receiptId,
    triage_level: triageLevel,
    patient: {
      name: payload.patient.name,
      phone_masked: masked,
      visit_type: payload.patient.visit_type,
    },
    summary: {
      main_symptom: payload.symptom.main_symptom,
      duration: payload.symptom.duration,
      severity_nrs: payload.symptom.severity_nrs,
      stress_level: payload.health_core.stress_level,
      constitution_hint: `${payload.constitution.heat_cold_sensitivity} / ${payload.constitution.digestion_pattern}`,
    },
  };
}
