import { NextRequest, NextResponse } from "next/server";
import type { PatientConsultInputV1 } from "@/lib/cdss-contract";
import { buildAdvancedConsultDraft } from "@/lib/cdss-inference";
import { validateLaneABirth } from "@/lib/global-birth-input";

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validateInput(body: PatientConsultInputV1): string | null {
  if (body.schema !== "patient_consult_input_v1") return "invalid_schema";
  if (!isNonEmptyString(body.request_id)) return "missing_request_id";
  if (!isNonEmptyString(body.actor_id)) return "missing_actor_id";
  const birthErr = validateLaneABirth(body.lane_a_profile || {});
  if (birthErr) return birthErr;
  if (!isNonEmptyString(body.lane_b_clinical?.chief_complaint)) return "missing_chief_complaint";
  if (!isNonEmptyString(body.lane_b_clinical?.onset)) return "missing_onset";
  if (!isNonEmptyString(body.lane_b_clinical?.severity)) return "missing_severity";
  return null;
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as PatientConsultInputV1;
    const invalid = validateInput(body);
    if (invalid) return NextResponse.json({ success: false, error: invalid }, { status: 400 });
    const draft = await buildAdvancedConsultDraft(body);
    return NextResponse.json(
      {
        success: true,
        draft,
        guardrail: {
          lane_separation: true,
          citation_enforced: draft.citations.length > 0,
          physician_confirmation_required: draft.requires_physician_confirmation === true,
        },
      },
      { status: 200, headers: { "Cache-Control": "no-store, no-cache, must-revalidate" } }
    );
  } catch (error: any) {
    return NextResponse.json({ success: false, error: `advanced_consult_failed: ${error?.message || "unknown"}` }, { status: 500 });
  }
}
