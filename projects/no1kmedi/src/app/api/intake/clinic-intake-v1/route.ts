import { NextRequest, NextResponse } from "next/server";
import { hasAdminTokenAccess } from "@/lib/internal-api-auth";
import { getPreSurveys, savePreSurveys, type PatientPreSurveyRecord } from "@/app/api/intake/_store";
import {
  buildKakaoSummary,
  computeClinicTriageLevel,
  normalizePhoneDigits,
  validateClinicIntakeV1,
  type ClinicIntakeV1Payload,
} from "@/lib/clinic-intake-v1-contract";
import { deliverClinicIntakeNotifications } from "@/lib/patient-intake-notification-v1";
import { extractSajuLabelFromVerifyLite, resolveClinicBirthInstant } from "@/lib/clinic-intake-birth-v1";
import { runVerifyLiteEngine } from "@/lib/manseryeok-verify-lite-engine";

function generateIntakePin(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let pin = "";
  for (let i = 0; i < 6; i += 1) pin += chars[Math.floor(Math.random() * chars.length)];
  return `${pin.slice(0, 3)}-${pin.slice(3)}`;
}

async function resolveSajuSnapshot(birthInstantUtc: string, ianaTz: string) {
  try {
    const lite = await runVerifyLiteEngine({
      birth_instant_utc: birthInstantUtc,
      tz: ianaTz,
    });
    const label = extractSajuLabelFromVerifyLite(lite.myeongni_lite);
    return {
      saju_label: label || undefined,
      saju_source: label ? ("live" as const) : ("pending" as const),
      myeongni_lite: lite.myeongni_lite,
    };
  } catch {
    return { saju_label: undefined, saju_source: "pending" as const, myeongni_lite: null };
  }
}

export async function POST(request: NextRequest) {
  try {
    const payload = (await request.json()) as ClinicIntakeV1Payload;
    const validation = validateClinicIntakeV1(payload);
    if (!validation.ok) {
      return NextResponse.json({ success: false, error: validation.error }, { status: 400 });
    }

    const triageLevel = computeClinicTriageLevel(payload);
    const intakePin = generateIntakePin();
    const submittedAt = payload.submitted_at_utc || new Date().toISOString();
    const surveyId = `clinic_intake_${Date.now()}`;

    const birthResolved = resolveClinicBirthInstant({
      birthdate: payload.patient.birthdate,
      birthTime: payload.optional_profile?.birth_time,
      birthTimeKnown: payload.optional_profile?.birth_time_known,
    });

    let saju_label: string | undefined;
    let saju_source: "live" | "fallback" | "pending" | undefined;
    if (birthResolved) {
      const saju = await resolveSajuSnapshot(birthResolved.birth_instant_utc, birthResolved.iana_tz);
      saju_label = saju.saju_label;
      saju_source = saju.saju_source;
    }

    const record: PatientPreSurveyRecord = {
      survey_id: surveyId,
      intake_pin: intakePin,
      submitted_at_utc: submittedAt,
      status: "patient_submitted",
      triage_level: triageLevel,
      patient: {
        name: payload.patient.name.trim(),
        phone: normalizePhoneDigits(payload.patient.phone),
        age_band: payload.patient.birthdate.trim(),
      },
      symptoms: {
        pain_area: payload.symptom.main_symptom.trim(),
        pain_scale_0_10: payload.symptom.severity_nrs,
        symptom_duration: payload.symptom.duration.trim(),
        consultation_goal: (payload.symptom.free_text || "").trim(),
      },
      reservation: {
        partner_clinic_preference: {
          region: (payload.clinic_preference?.region || "").trim(),
          specialty: (payload.clinic_preference?.specialty || "").trim(),
          preferred_time: (payload.clinic_preference?.preferred_time || "").trim(),
        },
      },
      lane_a_profile: {
        ...(birthResolved
          ? {
              birth_instant_utc: birthResolved.birth_instant_utc,
              iana_tz: birthResolved.iana_tz,
              birth_time_known: birthResolved.birth_time_known,
              birth_time_defaulted: birthResolved.birth_time_defaulted,
            }
          : {}),
        ...(saju_label ? { saju_label, saju_source } : saju_source ? { saju_source } : {}),
        constitution_survey: {
          schema_version: "clinic_intake_v1",
          sleep_pattern: payload.health_core.sleep_quality.trim(),
          digestion_pattern: payload.constitution.digestion_pattern.trim(),
          questionnaire_answers: {
            heat_cold_sensitivity: payload.constitution.heat_cold_sensitivity,
            fatigue_recovery: payload.constitution.fatigue_recovery,
            body_frame: payload.constitution.body_frame,
            temperament: payload.constitution.temperament,
          },
        },
      },
      safety: {
        red_flags: {
          chestPain: payload.red_flags.chestPain,
          breathingTrouble: false,
          paralysisOrSpeech: payload.red_flags.neuroDeficit,
          highFeverOrBleeding: payload.red_flags.highFever || payload.red_flags.pregnancyOrMajorCondition,
        },
      },
      consent: {
        privacy: payload.consent.sensitive_collection,
        medical: payload.consent.kakao_transfer,
      },
      meta: {
        source: "clinic_intake_v1",
        vocabulary_lane: "physician_gold",
      },
    };

    const rows = await getPreSurveys();
    rows.unshift(record);
    await savePreSurveys(rows);

    const kakaoSummary = buildKakaoSummary(payload, surveyId, triageLevel);
    record.meta = { ...(record.meta || {}), kakao_summary: kakaoSummary };
    rows[0] = record;
    await savePreSurveys(rows);
    const notification = await deliverClinicIntakeNotifications({ kakaoSummary });

    return NextResponse.json(
      {
        success: true,
        survey_id: surveyId,
        intake_pin: intakePin,
        triage_level: triageLevel,
        birth_resolved: Boolean(birthResolved),
        saju_label: saju_label || null,
        saju_source: saju_source || null,
        kakao_summary: kakaoSummary,
        kakao_delivery: notification.kakao_delivery,
        send_gate: notification.gate.send_gate,
        notification_lane: notification.policy.lane,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ success: false, error: `clinic_intake_v1_failed:${message}` }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  if (!hasAdminTokenAccess(request)) {
    return NextResponse.json({ success: false, error: "admin_token_required" }, { status: 401 });
  }
  const sourceFilter = request.nextUrl.searchParams.get("source") || "clinic_intake_v1";
  const all = await getPreSurveys();
  const rows = all
    .filter((row) => (row.meta?.source || "") === sourceFilter)
    .slice(0, 100)
    .map((row) => ({
      survey_id: row.survey_id,
      submitted_at_utc: row.submitted_at_utc,
      triage_level: row.triage_level,
      patient_name: row.patient.name,
      patient_phone: row.patient.phone,
      symptom: row.symptoms.pain_area,
      severity_nrs: row.symptoms.pain_scale_0_10,
      saju_label: row.lane_a_profile?.saju_label || "",
      birth_instant_utc: row.lane_a_profile?.birth_instant_utc || "",
      constitution_heat_cold:
        (row.lane_a_profile?.constitution_survey?.questionnaire_answers?.heat_cold_sensitivity as string | undefined) || "",
      constitution_fatigue_recovery:
        (row.lane_a_profile?.constitution_survey?.questionnaire_answers?.fatigue_recovery as string | undefined) || "",
      kakao_summary: row.meta?.kakao_summary || null,
    }));
  return NextResponse.json({ success: true, count: rows.length, rows }, { status: 200 });
}
