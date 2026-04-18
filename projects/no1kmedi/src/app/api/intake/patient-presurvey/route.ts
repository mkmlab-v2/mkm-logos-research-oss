/**
 * @MKM12-METADATA
 * Type: Engine
 * Vector: {S:0.86, L:0.74, K:0.78, M:0.61}
 * Balance: 93
 * Purpose: Receive patient pre-survey and triage for clinician review queue.
 * Keywords: Next.js, intake, triage, consent, webhook
 */
import { NextRequest, NextResponse } from "next/server";
import {
  getPreSurveys,
  getReservations,
  savePreSurveys,
  saveReservations,
  type PatientPreSurveyRecord,
  type PartnerReservationRecord,
} from "@/app/api/intake/_store";

type PreSurveyPayload = {
  name: string;
  phone: string;
  age_band: string;
  pain_area: string;
  pain_scale_0_10: number;
  symptom_duration: string;
  constitution_survey?: {
    schema_version?: string;
    sleep_pattern?: string;
    digestion_pattern?: string;
    questionnaire_answers?: Record<string, "a" | "b" | "">;
  };
  red_flags?: {
    chestPain?: boolean;
    breathingTrouble?: boolean;
    paralysisOrSpeech?: boolean;
    highFeverOrBleeding?: boolean;
  };
  consultation_goal?: string;
  partner_clinic_preference?: {
    region?: string;
    specialty?: string;
    preferred_time?: string;
  };
  consent: {
    privacy: boolean;
    medical: boolean;
  };
};

type ReservationRequestPayload = {
  reservation_request: {
    survey_id: string;
    clinic_id: string;
    clinic_name: string;
    patient_name: string;
    patient_phone: string;
  };
};

type PartnerClinic = {
  id: string;
  name: string;
  region: string;
  specialties: string[];
  available_times: string[];
};

const PARTNER_CLINICS: PartnerClinic[] = [
  {
    id: "clinic_gwangmyeong_baekje",
    name: "광명백제한의원",
    region: "광명",
    specialties: ["pain", "digestive", "sleep"],
    available_times: ["weekday_morning", "weekday_afternoon", "weekday_evening", "weekend"],
  },
  {
    id: "clinic_gangnam_mkm",
    name: "강남MKM한의원",
    region: "강남",
    specialties: ["pain", "women", "sleep"],
    available_times: ["weekday_afternoon", "weekday_evening", "weekend"],
  },
  {
    id: "clinic_songpa_balance",
    name: "송파밸런스한의원",
    region: "송파",
    specialties: ["digestive", "women", "other"],
    available_times: ["weekday_morning", "weekday_afternoon"],
  },
  {
    id: "clinic_mapo_life",
    name: "마포라이프한의원",
    region: "마포",
    specialties: ["sleep", "other", "digestive"],
    available_times: ["weekday_evening", "weekend"],
  },
];

function isNonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isReservationRequestPayload(value: unknown): value is ReservationRequestPayload {
  if (!value || typeof value !== "object") return false;
  const request = (value as ReservationRequestPayload).reservation_request;
  if (!request || typeof request !== "object") return false;
  return (
    isNonEmpty(request.survey_id) &&
    isNonEmpty(request.clinic_id) &&
    isNonEmpty(request.clinic_name) &&
    isNonEmpty(request.patient_name) &&
    isNonEmpty(request.patient_phone)
  );
}

function recommendPartnerClinics(payload: PreSurveyPayload): PartnerClinic[] {
  const region = (payload.partner_clinic_preference?.region || "").trim().toLowerCase();
  const specialty = (payload.partner_clinic_preference?.specialty || "").trim();
  const preferredTime = (payload.partner_clinic_preference?.preferred_time || "").trim();

  const scored = PARTNER_CLINICS.map((clinic) => {
    let score = 0;
    if (region && clinic.region.toLowerCase().includes(region)) score += 3;
    if (specialty && clinic.specialties.includes(specialty)) score += 2;
    if (preferredTime && clinic.available_times.includes(preferredTime)) score += 1;
    return { clinic, score };
  });

  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map((entry) => entry.clinic);
}

function computeTriage(redFlags: PreSurveyPayload["red_flags"], painScale: number): "routine" | "priority" | "emergency" {
  const emergency = Boolean(
    redFlags?.chestPain || redFlags?.breathingTrouble || redFlags?.paralysisOrSpeech || redFlags?.highFeverOrBleeding,
  );
  if (emergency) return "emergency";
  if (painScale >= 8) return "priority";
  return "routine";
}

function validate(payload: PreSurveyPayload): string | null {
  if (!isNonEmpty(payload.name)) return "name_required";
  if (!isNonEmpty(payload.phone)) return "phone_required";
  if (!isNonEmpty(payload.age_band)) return "age_band_required";
  if (!isNonEmpty(payload.pain_area)) return "pain_area_required";
  if (!Number.isFinite(payload.pain_scale_0_10) || payload.pain_scale_0_10 < 0 || payload.pain_scale_0_10 > 10) {
    return "pain_scale_invalid";
  }
  if (!isNonEmpty(payload.symptom_duration)) return "symptom_duration_required";
  if (!payload.consent?.privacy || !payload.consent?.medical) return "consent_required";
  return null;
}

async function sendWebhook(url: string, body: Record<string, unknown>) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    return { delivered: res.ok, status: res.status };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_webhook_error";
    return { delivered: false, error: message };
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as unknown;
    if (isReservationRequestPayload(body)) {
      const reservation: PartnerReservationRecord = {
        reservation_request_id: `reservation_${Date.now()}`,
        requested_at_utc: new Date().toISOString(),
        status: "requested",
        survey_id: body.reservation_request.survey_id,
        clinic_id: body.reservation_request.clinic_id,
        clinic_name: body.reservation_request.clinic_name,
        patient_name: body.reservation_request.patient_name,
        patient_phone: body.reservation_request.patient_phone,
        updated_at_utc: new Date().toISOString(),
      };
      const rows = await getReservations();
      rows.unshift(reservation);
      await saveReservations(rows);
      console.log("[patient-presurvey-reservation]", JSON.stringify(reservation));
      return NextResponse.json(
        {
          success: true,
          reservation_request_id: reservation.reservation_request_id,
          message: "제휴 한의원 예약 요청이 접수되었습니다.",
        },
        { status: 200, headers: { "Cache-Control": "no-store" } },
      );
    }

    const payload = body as PreSurveyPayload;
    const invalid = validate(payload);
    if (invalid) return NextResponse.json({ success: false, error: invalid }, { status: 400 });

    const triageLevel = computeTriage(payload.red_flags, Number(payload.pain_scale_0_10));
    const recommendedClinics = recommendPartnerClinics(payload);
    const survey: PatientPreSurveyRecord = {
      survey_id: `presurvey_${Date.now()}`,
      submitted_at_utc: new Date().toISOString(),
      status: "patient_submitted",
      triage_level: triageLevel,
      patient: {
        name: payload.name.trim(),
        phone: payload.phone.trim(),
        age_band: payload.age_band.trim(),
      },
      symptoms: {
        pain_area: payload.pain_area.trim(),
        pain_scale_0_10: Number(payload.pain_scale_0_10),
        symptom_duration: payload.symptom_duration.trim(),
        consultation_goal: (payload.consultation_goal || "").trim(),
      },
      reservation: {
        partner_clinic_preference: {
          region: (payload.partner_clinic_preference?.region || "").trim(),
          specialty: (payload.partner_clinic_preference?.specialty || "").trim(),
          preferred_time: (payload.partner_clinic_preference?.preferred_time || "").trim(),
        },
      },
      lane_a_profile: {
        constitution_survey: {
          schema_version: payload.constitution_survey?.schema_version || "",
          sleep_pattern: payload.constitution_survey?.sleep_pattern || "",
          digestion_pattern: payload.constitution_survey?.digestion_pattern || "",
          questionnaire_answers: payload.constitution_survey?.questionnaire_answers || {},
        },
      },
      safety: {
        red_flags: payload.red_flags || {},
      },
      consent: payload.consent,
    };
    const surveys = await getPreSurveys();
    surveys.unshift(survey);
    await savePreSurveys(surveys);

    const webhookUrl = process.env.PATIENT_PRESURVEY_WEBHOOK_URL?.trim();
    let webhook: Record<string, unknown> = { enabled: false, delivered: false };
    if (webhookUrl) {
      webhook = { enabled: true, ...(await sendWebhook(webhookUrl, survey)) };
    }

    console.log("[patient-presurvey]", JSON.stringify(survey));

    return NextResponse.json(
      {
        success: true,
        survey_id: survey.survey_id,
        triage_level: triageLevel,
        recommended_partner_clinics: recommendedClinics,
        emergency_notice:
          triageLevel === "emergency" ? "응급 신호가 감지되었습니다. 즉시 119 또는 응급실 이용이 우선입니다." : undefined,
        webhook,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ success: false, error: `patient_presurvey_failed:${message}` }, { status: 500 });
  }
}
