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

function generateIntakePin(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let pin = "";
  for (let i = 0; i < 6; i += 1) {
    pin += chars[Math.floor(Math.random() * chars.length)];
  }
  return `${pin.slice(0, 3)}-${pin.slice(3)}`;
}

function normalizePin(value: string): string {
  return value.replace(/[^A-Z0-9]/gi, "").toUpperCase();
}

function normalizePhoneDigits(value: string): string {
  return value.replace(/\D/g, "");
}

const LOOKUP_WINDOW_MS = 10 * 60 * 1000;
const LOOKUP_MAX_FAILS = 5;
const lookupFailures = new Map<string, { count: number; resetAt: number }>();
const LOOKUP_DELAY_MS_MIN = 600;
const LOOKUP_DELAY_MS_MAX = 1200;
const LOOKUP_ALERT_WINDOW_MS = 10 * 60 * 1000;
const LOOKUP_ALERT_FAIL_THRESHOLD = 20;
const lookupIpFailures = new Map<string, { count: number; resetAt: number; alertedAt: number }>();
const LOOKUP_ALERT_WEBHOOK_URL = (process.env.PIN_LOOKUP_ALERT_WEBHOOK_URL || "").trim();
const LOOKUP_IP_ALLOWLIST = (process.env.PIN_LOOKUP_IP_ALLOWLIST || "")
  .split(",")
  .map((v) => v.trim())
  .filter(Boolean);

function lookupThrottleKey(request: NextRequest, pin: string): string {
  const forwarded = request.headers.get("x-forwarded-for") || "";
  const ip = forwarded.split(",")[0]?.trim() || "unknown";
  return `${ip}:${pin}`;
}

function extractClientIp(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-for") || "";
  return forwarded.split(",")[0]?.trim() || "unknown";
}

function isAllowlistedIp(ip: string): boolean {
  return LOOKUP_IP_ALLOWLIST.includes(ip);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomLookupDelayMs(): number {
  return LOOKUP_DELAY_MS_MIN + Math.floor(Math.random() * (LOOKUP_DELAY_MS_MAX - LOOKUP_DELAY_MS_MIN + 1));
}

function logPinLookupEvent(
  event: "lookup_success" | "lookup_failed" | "lookup_blocked",
  payload: { request: NextRequest; pin: string; patientName?: string; phoneLast4?: string; failCount?: number; reason?: string },
) {
  const ip = extractClientIp(payload.request);
  const maskedPin = payload.pin ? `${payload.pin.slice(0, 2)}***${payload.pin.slice(-1)}` : "";
  const maskedName = payload.patientName ? `${payload.patientName.slice(0, 1)}*` : "";
  const safePhoneLast4 = payload.phoneLast4 ? `**${payload.phoneLast4.slice(-2)}` : "";
  console.log(
    "[patient-presurvey-pin-lookup]",
    JSON.stringify({
      event,
      ip,
      pin: maskedPin,
      name: maskedName,
      phone_last4: safePhoneLast4,
      fail_count: payload.failCount ?? 0,
      reason: payload.reason || "",
      at_utc: new Date().toISOString(),
    }),
  );
}

async function sendLookupAlertWebhook(payload: Record<string, unknown>) {
  if (!LOOKUP_ALERT_WEBHOOK_URL) return;
  try {
    const isSlackWebhook = LOOKUP_ALERT_WEBHOOK_URL.includes("hooks.slack.com/services/");
    const body = isSlackWebhook
      ? {
          text: `[jema-ai] PIN lookup alert - ${String(payload.event || "unknown_event")} (ip:${String(payload.ip || "unknown")}, count:${String(payload.count || 0)})`,
          ...payload,
        }
      : payload;
    await fetch(LOOKUP_ALERT_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_webhook_error";
    console.warn(
      "[patient-presurvey-pin-lookup-alert-webhook-failed]",
      JSON.stringify({ error: message, at_utc: new Date().toISOString() }),
    );
  }
}

async function recordIpFailureAndMaybeAlert(request: NextRequest): Promise<number> {
  const ip = extractClientIp(request);
  const now = Date.now();
  const prev = lookupIpFailures.get(ip);
  const current = !prev || prev.resetAt <= now ? { count: 0, resetAt: now + LOOKUP_ALERT_WINDOW_MS, alertedAt: 0 } : prev;
  const nextCount = current.count + 1;
  const next = { ...current, count: nextCount };
  lookupIpFailures.set(ip, next);

  if (nextCount >= LOOKUP_ALERT_FAIL_THRESHOLD && (!next.alertedAt || now - next.alertedAt >= LOOKUP_ALERT_WINDOW_MS)) {
    next.alertedAt = now;
    lookupIpFailures.set(ip, next);
    const alertPayload = {
      event: "ip_lookup_fail_threshold_reached",
      service: "jema-ai",
      environment: process.env.NODE_ENV || "production",
      domain: "jema-ai.com",
      ip,
      count: nextCount,
      threshold: LOOKUP_ALERT_FAIL_THRESHOLD,
      window_ms: LOOKUP_ALERT_WINDOW_MS,
      at_utc: new Date().toISOString(),
    };
    console.warn("[patient-presurvey-pin-lookup-alert]", JSON.stringify(alertPayload));
    await sendLookupAlertWebhook(alertPayload);
  }

  return nextCount;
}

const PARTNER_CLINICS: PartnerClinic[] = [
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

export async function GET(request: NextRequest) {
  try {
    const pin = normalizePin(request.nextUrl.searchParams.get("pin") || "");
    const patientName = (request.nextUrl.searchParams.get("name") || "").trim();
    const phoneLast4 = normalizePhoneDigits(request.nextUrl.searchParams.get("phone_last4") || "");

    if (!pin) {
      return NextResponse.json({ success: false, error: "pin_required" }, { status: 400 });
    }
    if (!patientName && phoneLast4.length !== 4) {
      return NextResponse.json(
        { success: false, error: "second_factor_required" },
        { status: 400, headers: { "Cache-Control": "no-store" } },
      );
    }

    const throttleKey = lookupThrottleKey(request, pin);
    const clientIp = extractClientIp(request);
    const skipThrottleForAllowlist = isAllowlistedIp(clientIp);
    const skipDelayForAllowlist = skipThrottleForAllowlist;
    const now = Date.now();
    const throttle = lookupFailures.get(throttleKey);
    if (!skipThrottleForAllowlist && throttle && throttle.resetAt > now && throttle.count >= LOOKUP_MAX_FAILS) {
      const retryAfterSec = Math.max(1, Math.ceil((throttle.resetAt - now) / 1000));
      logPinLookupEvent("lookup_blocked", {
        request,
        pin,
        patientName,
        phoneLast4,
        failCount: throttle.count,
        reason: "too_many_lookup_attempts",
      });
      if (!skipDelayForAllowlist) await sleep(randomLookupDelayMs());
      return NextResponse.json(
        { success: false, error: "too_many_lookup_attempts", retry_after_seconds: retryAfterSec },
        { status: 429, headers: { "Cache-Control": "no-store" } },
      );
    }

    const surveys = await getPreSurveys();
    const found = surveys.find((row) => {
      const rowPin = normalizePin(row.intake_pin || "");
      if (rowPin !== pin) return false;
      const sameName = patientName ? row.patient.name.trim() === patientName : true;
      const samePhone = phoneLast4 ? normalizePhoneDigits(row.patient.phone).endsWith(phoneLast4) : true;
      return sameName && samePhone;
    });

    if (!found) {
      const base = throttle && throttle.resetAt > now ? throttle : { count: 0, resetAt: now + LOOKUP_WINDOW_MS };
      const nextCount = base.count + 1;
      lookupFailures.set(throttleKey, { count: nextCount, resetAt: base.resetAt });
      const ipFailCount = await recordIpFailureAndMaybeAlert(request);
      logPinLookupEvent("lookup_failed", {
        request,
        pin,
        patientName,
        phoneLast4,
        failCount: nextCount,
        reason: `pin_not_found_or_mismatch(ip_fail_count:${ipFailCount})`,
      });
      if (!skipDelayForAllowlist) await sleep(randomLookupDelayMs());
      return NextResponse.json(
        { success: false, error: "pin_not_found_or_mismatch" },
        { status: 404, headers: { "Cache-Control": "no-store" } },
      );
    }

    lookupFailures.delete(throttleKey);
    logPinLookupEvent("lookup_success", {
      request,
      pin,
      patientName,
      phoneLast4,
      reason: "matched",
    });

    return NextResponse.json(
      {
        success: true,
        survey: {
          survey_id: found.survey_id,
          intake_pin: found.intake_pin || "",
          triage_level: found.triage_level,
          patient_name: found.patient.name,
          symptoms: found.symptoms,
          constitution_survey: found.lane_a_profile.constitution_survey,
          lane_a_profile: {
            birth_instant_utc: found.lane_a_profile.birth_instant_utc,
            iana_tz: found.lane_a_profile.iana_tz,
            birth_time_known: found.lane_a_profile.birth_time_known,
            saju_label: found.lane_a_profile.saju_label,
            saju_source: found.lane_a_profile.saju_source,
          },
        },
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ success: false, error: `patient_presurvey_lookup_failed:${message}` }, { status: 500 });
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
    const intakePin = generateIntakePin();
    const survey: PatientPreSurveyRecord = {
      survey_id: `presurvey_${Date.now()}`,
      intake_pin: intakePin,
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
        intake_pin: intakePin,
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
