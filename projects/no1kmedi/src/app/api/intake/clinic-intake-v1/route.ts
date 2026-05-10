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
import { deliverKakaoIntakeSummary } from "@/lib/kakao-intake-adapter";

function generateIntakePin(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let pin = "";
  for (let i = 0; i < 6; i += 1) pin += chars[Math.floor(Math.random() * chars.length)];
  return `${pin.slice(0, 3)}-${pin.slice(3)}`;
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
        constitution_survey: {
          schema_version: "clinic_intake_v1",
          sleep_pattern: payload.health_core.sleep_quality.trim(),
          digestion_pattern: payload.constitution.digestion_pattern.trim(),
          questionnaire_answers: {
            heat_cold_sensitivity: payload.constitution.heat_cold_sensitivity,
            fatigue_recovery: payload.constitution.fatigue_recovery,
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
      },
    };

    const rows = await getPreSurveys();
    rows.unshift(record);
    await savePreSurveys(rows);

    const kakaoSummary = buildKakaoSummary(payload, surveyId, triageLevel);
    record.meta = { ...(record.meta || {}), kakao_summary: kakaoSummary };
    rows[0] = record;
    await savePreSurveys(rows);
    const kakaoDelivery = await deliverKakaoIntakeSummary(process.env.KAKAO_CLINIC_INTAKE_WEBHOOK_URL, kakaoSummary);

    return NextResponse.json(
      {
        success: true,
        survey_id: surveyId,
        intake_pin: intakePin,
        triage_level: triageLevel,
        kakao_summary: kakaoSummary,
        kakao_delivery: kakaoDelivery,
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
      constitution_heat_cold:
        (row.lane_a_profile?.constitution_survey?.questionnaire_answers?.heat_cold_sensitivity as string | undefined) || "",
      constitution_fatigue_recovery:
        (row.lane_a_profile?.constitution_survey?.questionnaire_answers?.fatigue_recovery as string | undefined) || "",
      kakao_summary: row.meta?.kakao_summary || null,
    }));
  return NextResponse.json({ success: true, count: rows.length, rows }, { status: 200 });
}
