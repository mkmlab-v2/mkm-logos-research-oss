import { NextRequest, NextResponse } from "next/server";
import { getPreSurveys, savePreSurveys, type PatientPreSurveyRecord } from "@/app/api/intake/_store";
import {
  KAKAO_INTAKE_SCHEMA_VERSION,
  normalizePhoneDigits,
  type KakaoSurveyPayload,
  validateKakaoSurveyPayload,
} from "@/lib/kakao-intake-contract";
import { buildClinicianOrchestratorPrompt, buildSoapSeedFromKakaoSurvey } from "@/lib/clinician-soap-orchestrator";

function generateIntakePin(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let pin = "";
  for (let i = 0; i < 6; i += 1) pin += chars[Math.floor(Math.random() * chars.length)];
  return `${pin.slice(0, 3)}-${pin.slice(3)}`;
}

function computeTriage(payload: KakaoSurveyPayload): "routine" | "priority" | "emergency" {
  const rf = payload.health.red_flags;
  const emergency = Boolean(rf?.chestPain || rf?.breathingTrouble || rf?.paralysisOrSpeech || rf?.highFeverOrBleeding);
  if (emergency) return "emergency";
  if (payload.health.pain_scale_0_10 >= 8) return "priority";
  return "routine";
}

export async function POST(request: NextRequest) {
  try {
    const payload = (await request.json()) as KakaoSurveyPayload;
    const validation = validateKakaoSurveyPayload(payload);
    if (!validation.ok) {
      return NextResponse.json(
        { success: false, error: validation.error, constitution_core_answered_count: validation.constitution_core_answered_count },
        { status: 400 },
      );
    }

    const triageLevel = computeTriage(payload);
    const intakePin = generateIntakePin();
    const survey: PatientPreSurveyRecord = {
      survey_id: `kakao_presurvey_${Date.now()}`,
      intake_pin: intakePin,
      submitted_at_utc: payload.submitted_at_utc || new Date().toISOString(),
      status: "patient_submitted",
      triage_level: triageLevel,
      patient: {
        name: payload.patient.name.trim(),
        phone: normalizePhoneDigits(payload.patient.phone),
        age_band: payload.patient.age_band.trim(),
      },
      symptoms: {
        pain_area: payload.health.pain_area.trim(),
        pain_scale_0_10: Number(payload.health.pain_scale_0_10),
        symptom_duration: payload.health.symptom_duration.trim(),
        consultation_goal: payload.health.chief_complaint.trim(),
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
          schema_version: KAKAO_INTAKE_SCHEMA_VERSION,
          sleep_pattern: payload.health.sleep_pattern,
          digestion_pattern: payload.health.digestion_pattern,
          questionnaire_answers: payload.constitution.questionnaire_answers,
        },
      },
      safety: {
        red_flags: payload.health.red_flags || {},
      },
      consent: payload.consent,
    };

    const rows = await getPreSurveys();
    rows.unshift(survey);
    await savePreSurveys(rows);

    const soapSeed = buildSoapSeedFromKakaoSurvey(payload);
    const orchestratorPrompt = buildClinicianOrchestratorPrompt(soapSeed);

    return NextResponse.json(
      {
        success: true,
        survey_id: survey.survey_id,
        intake_pin: intakePin,
        triage_level: triageLevel,
        constitution_core_answered_count: validation.constitution_core_answered_count,
        clinician_handoff: {
          lane: "clinician",
          soap_seed: soapSeed,
          orchestrator_prompt: orchestratorPrompt,
          note: "Paste into /clinician chat as structured context. Final diagnosis/treatment must be clinician-confirmed.",
        },
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ success: false, error: `kakao_survey_failed:${message}` }, { status: 500 });
  }
}
