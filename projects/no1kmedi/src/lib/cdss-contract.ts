export type SasangType = "taeyang" | "taeeum" | "soyag" | "soeum" | "unknown";

export type PatientConsultInputV1 = {
  schema: "patient_consult_input_v1";
  request_id: string;
  actor_id: string;
  lane_a_profile: {
    /** @deprecated Prefer birth_instant_utc + iana_tz for global/DST-safe resolution. */
    birth_datetime?: string;
    /** Absolute birth instant (ISO 8601, Z or numeric offset). */
    birth_instant_utc?: string;
    /** IANA timezone id (e.g. Asia/Seoul). */
    iana_tz?: string;
    constitution_survey: {
      body_heat_preference?: string;
      digestion_pattern?: string;
      sleep_pattern?: string;
      stress_reactivity?: string;
      free_text?: string;
    };
  };
  lane_b_clinical: {
    chief_complaint: string;
    onset: string;
    severity: string;
    medication: string;
    health_survey: {
      appetite?: string;
      bowel_pattern?: string;
      sleep_quality?: string;
      pain_scale_0_10?: number;
      red_flag_notes?: string;
    };
  };
};

export type CdssCitationV1 = {
  citation_id: string;
  source_title: string;
  source_excerpt: string;
  source_ref: string;
  evidence_level: "A" | "B" | "C";
};

export type ConsultDraftV1 = {
  schema: "consult_draft_v1";
  request_id: string;
  mode: "cdss_draft";
  profile_summary: {
    sasang_candidate: SasangType;
    saju_reference: string;
    saju_source: "live" | "fallback";
  };
  clinical_summary: string;
  reasoning: {
    syndrome_hypothesis: string;
    care_direction: string;
    caution: string;
  };
  citations: CdssCitationV1[];
  requires_physician_confirmation: true;
  non_medical_notice: string;
};
