/**
 * Consumer-only IWS v2 preview — mkmlife / personadiary surfaces (no Pro gate).
 */

import type { PatientConsultInputV1 } from "./cdss-contract";
import { validateLaneABirth } from "./global-birth-input";

export type IntegratedWellnessConsumerPreviewRequest = {
  request_id: string;
  birth_instant_utc: string;
  iana_tz: string;
  gender?: "male" | "female" | "other" | "unspecified";
  chief_complaint?: string;
  sasang_candidate?: string;
};

const SASANG_NORMALIZE: Record<string, string> = {
  taeyang: "taeyang",
  soyag: "soyang",
  soyang: "soyang",
  soyangi: "soyang",
  taeeum: "taeum",
  taeum: "taeum",
  soeum: "soeum",
  unknown: "unknown",
};

export function buildConsumerConsultFromPreview(
  body: IntegratedWellnessConsumerPreviewRequest,
): { ok: true; consult: PatientConsultInputV1; sasangCandidate: string } | { ok: false; error: string } {
  if (!body.request_id?.trim()) {
    return { ok: false, error: "missing_request_id" };
  }
  const laneA = {
    birth_instant_utc: body.birth_instant_utc?.trim(),
    iana_tz: body.iana_tz?.trim() || "Asia/Seoul",
    constitution_survey: {},
  };
  const birthErr = validateLaneABirth(laneA);
  if (birthErr) {
    return { ok: false, error: birthErr };
  }

  const consult: PatientConsultInputV1 = {
    schema: "patient_consult_input_v1",
    request_id: body.request_id.trim(),
    actor_id: "consumer_mkmlife_preview",
    lane_a_profile: laneA,
    lane_b_clinical: {
      chief_complaint: (body.chief_complaint || "웰니스 상담").trim(),
      onset: "unknown",
      severity: "mild",
      medication: "none_reported",
      health_survey: {},
    },
  };

  const raw = (body.sasang_candidate || "unknown").toLowerCase();
  const sasangCandidate = SASANG_NORMALIZE[raw] || "unknown";

  return { ok: true, consult, sasangCandidate };
}

export const MKMLIFE_CORS_ORIGINS = [
  "https://mkmlife.com",
  "https://www.mkmlife.com",
  "http://localhost:3000",
  "http://127.0.0.1:3000",
];

export function corsHeadersForOrigin(origin: string | null): Record<string, string> {
  if (origin && MKMLIFE_CORS_ORIGINS.includes(origin)) {
    return {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      Vary: "Origin",
    };
  }
  return {};
}
