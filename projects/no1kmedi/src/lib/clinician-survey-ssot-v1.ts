/** Clinician vs consumer survey lane pointers (MKM_DOMAIN_CLINICAL_LANE_V1 §3). */
export type ClinicianSurveySsotPayload = {
  success: boolean;
  error?: string;
  pack_id?: string;
  pack_schema?: string;
  item_count?: number;
  lane?: string;
  research_only?: boolean;
  physician_lane: {
    presurvey_api: string;
    constitution_questions_in_app: number;
    ssot_bank_path: string;
    /** 원내 A4 인쇄용지 — 앱 설문보다 우선 (physician_gold) */
    print_form_path: string;
    print_form_label_ko: string;
  };
  consumer_lane: {
    survey_url: string;
    score_api_path: string;
    label: string;
    sublabel: string;
  };
  disclaimer: string;
};

export function defaultMkmlifeConsumerSurveyUrl(): string {
  return (
    process.env.NEXT_PUBLIC_MKMLIFE_CONSUMER_SURVEY_URL?.trim() ||
    "https://mkmlife.com/ask-one"
  );
}
