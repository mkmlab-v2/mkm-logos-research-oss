/**
 * Build `patient_consult_input_v1` from clinician form state (shared by CDSS + bundle APIs).
 */

import type { PatientConsultInputV1 } from "./cdss-contract";

export type ClinicianConsultFormState = {
  /** Demo / SSOT patient slug when survey context is not loaded */
  ssotSlug?: string;
  actorId: string;
  birthInstantUtc: string;
  ianaTz: string;
  chiefComplaint: string;
  onset: string;
  severity: string;
  medication: string;
  digestionPattern: string;
  sleepPattern: string;
  bodyHeatPreference: string;
  stressReactivity: string;
  constitutionFreeText: string;
  painScale0to10: string;
  redFlagNotes: string;
  healthAppetite: string;
  healthBowelPattern: string;
  loadedSurveyContext: {
    surveyId: string;
    intakePin: string;
    patientName: string;
    triageLevel: "routine" | "priority" | "emergency";
  } | null;
};

export function buildClinicianConsultPayload(
  state: ClinicianConsultFormState,
  requestId: string,
): PatientConsultInputV1 {
  return {
    schema: "patient_consult_input_v1",
    request_id: requestId,
    actor_id: state.actorId,
    lane_a_profile: {
      birth_instant_utc: state.birthInstantUtc.trim(),
      iana_tz: state.ianaTz.trim(),
      constitution_survey: {
        digestion_pattern: state.digestionPattern,
        sleep_pattern: state.sleepPattern,
        ...(state.bodyHeatPreference.trim() ? { body_heat_preference: state.bodyHeatPreference.trim() } : {}),
        ...(state.stressReactivity.trim() ? { stress_reactivity: state.stressReactivity.trim() } : {}),
        ...(state.constitutionFreeText.trim() ? { free_text: state.constitutionFreeText.trim() } : {}),
      },
    },
    lane_b_clinical: {
      chief_complaint: state.chiefComplaint,
      onset: state.onset,
      severity: state.severity,
      medication: state.medication,
      patient_intake_context: state.loadedSurveyContext
        ? {
            survey_id: state.loadedSurveyContext.surveyId,
            intake_pin: state.loadedSurveyContext.intakePin,
            patient_name: state.loadedSurveyContext.patientName,
            triage_level: state.loadedSurveyContext.triageLevel,
          }
        : undefined,
      health_survey: {
        sleep_quality: state.sleepPattern,
        ...(state.redFlagNotes.trim() ? { red_flag_notes: state.redFlagNotes.trim() } : {}),
        ...(state.healthAppetite.trim() ? { appetite: state.healthAppetite.trim() } : {}),
        ...(state.healthBowelPattern.trim() ? { bowel_pattern: state.healthBowelPattern.trim() } : {}),
        ...(state.painScale0to10.trim() !== "" && !Number.isNaN(Number(state.painScale0to10))
          ? {
              pain_scale_0_10: Math.min(10, Math.max(0, Math.round(Number(state.painScale0to10)))),
            }
          : {}),
      },
    },
  };
}

export function buildSoapStubFromConsultDraft(draft: {
  clinical_summary: string;
  reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
}): Record<string, { text: string }> {
  return {
    subjective: { text: draft.clinical_summary || "(CDSS 임상 요약 — 한의사 확정 후 갱신)" },
    objective: { text: "진찰·맥진·설문 등 객관 소견은 담당 한의사가 확정합니다." },
    assessment: { text: draft.reasoning.syndrome_hypothesis || "(변증·평가 — 한의사 확정)" },
    plan: { text: draft.reasoning.care_direction || "(계획 — 한의사 확정)" },
  };
}
