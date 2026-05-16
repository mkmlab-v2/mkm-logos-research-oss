import { NextRequest, NextResponse } from "next/server";
import type { PatientConsultInputV1 } from "@/lib/cdss-contract";
import { buildAdvancedConsultDraft } from "@/lib/cdss-inference";
import { validateLaneABirth } from "@/lib/global-birth-input";
import { buildKmCdsEnvelopePipeline } from "@/lib/km-cds-envelope-pipeline-v1";
import { shouldValidateKmCdsEnvelopeViaPython } from "@/lib/km-cds-envelope-python-bridge-v1";

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
    const literatureInjectedCount = draft.citations.filter((c) => {
      const idBased = c.citation_id.startsWith("lit_");
      const refBased = c.source_ref.toLowerCase().startsWith("epmc:");
      return idBased || refBased;
    }).length;

    const validateEnvelope =
      request.nextUrl.searchParams.get("validate_km_cds_envelope") === "1" || shouldValidateKmCdsEnvelopeViaPython();
    const kmPipeline = buildKmCdsEnvelopePipeline(body, draft, { skipPython: !validateEnvelope });

    return NextResponse.json(
      {
        success: true,
        draft,
        evidence_meta: {
          literature_count_rule_version: "v2_id_or_epmc_ref",
          citation_count: draft.citations.length,
          literature_injected_count: literatureInjectedCount,
        },
        guardrail: {
          lane_separation: true,
          citation_enforced: draft.citations.length > 0,
          physician_confirmation_required: draft.requires_physician_confirmation === true,
        },
        km_cds: {
          payload: kmPipeline.payload,
          envelope: kmPipeline.ok ? kmPipeline.envelope : undefined,
          tri_layer: kmPipeline.tri_layer,
          validation: validateEnvelope
            ? {
                ok: kmPipeline.ok,
                method: kmPipeline.ok ? "python" : "python",
                error: kmPipeline.ok ? undefined : kmPipeline.error,
              }
            : { ok: false, method: "skipped", error: "validation not requested" },
        },
      },
      { status: 200, headers: { "Cache-Control": "no-store, no-cache, must-revalidate" } }
    );
  } catch (error: any) {
    return NextResponse.json({ success: false, error: `advanced_consult_failed: ${error?.message || "unknown"}` }, { status: 500 });
  }
}
