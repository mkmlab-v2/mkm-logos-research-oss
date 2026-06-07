import type { ClinicianConsultFormState } from "@/lib/clinician-consult-payload-v1";

export type PatientPinLookupSurvey = {
  survey_id: string;
  intake_pin: string;
  triage_level: "routine" | "priority" | "emergency";
  patient_name: string;
  symptoms: {
    pain_area: string;
    pain_scale_0_10: number;
    symptom_duration: string;
    consultation_goal: string;
  };
  constitution_survey: {
    sleep_pattern: string;
    digestion_pattern: string;
    questionnaire_answers?: Record<string, string>;
  };
  lane_a_profile?: {
    birth_instant_utc?: string;
    iana_tz?: string;
    birth_time_known?: boolean;
    saju_label?: string;
    saju_source?: "live" | "fallback" | "pending";
  };
};

export type PatientPinLookupResponse = {
  success: boolean;
  error?: string;
  retry_after_seconds?: number;
  survey?: PatientPinLookupSurvey;
};

export function applyPatientPinSurveyToClinicianState(
  survey: PatientPinLookupSurvey,
  current: Pick<
    ClinicianConsultFormState,
    "chiefComplaint" | "onset" | "severity" | "digestionPattern" | "sleepPattern" | "painScale0to10" | "bodyHeatPreference" | "constitutionFreeText"
  >,
): Partial<ClinicianConsultFormState> {
  const mergedComplaint = [survey.symptoms.pain_area, survey.symptoms.consultation_goal].filter(Boolean).join(" / ");
  const qa = survey.constitution_survey.questionnaire_answers || {};
  const heatCold = qa.heat_cold_sensitivity || "";
  const fatigue = qa.fatigue_recovery || "";
  const constitutionNotes = [heatCold && `한·냉: ${heatCold}`, fatigue && `피로 회복: ${fatigue}`].filter(Boolean).join(" · ");

  return {
    chiefComplaint: mergedComplaint || survey.symptoms.pain_area || current.chiefComplaint,
    onset: survey.symptoms.symptom_duration || current.onset,
    severity: `${survey.symptoms.pain_scale_0_10}/10`,
    digestionPattern: survey.constitution_survey.digestion_pattern || current.digestionPattern,
    sleepPattern: survey.constitution_survey.sleep_pattern || current.sleepPattern,
    painScale0to10: String(survey.symptoms.pain_scale_0_10),
    bodyHeatPreference: heatCold || current.bodyHeatPreference,
    constitutionFreeText: constitutionNotes || current.constitutionFreeText,
    birthInstantUtc: survey.lane_a_profile?.birth_instant_utc?.trim() || "",
    ianaTz: survey.lane_a_profile?.iana_tz?.trim() || "Asia/Seoul",
    loadedSurveyContext: {
      surveyId: survey.survey_id,
      intakePin: survey.intake_pin,
      patientName: survey.patient_name,
      triageLevel: survey.triage_level,
    },
  };
}
