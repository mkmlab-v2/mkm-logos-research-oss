/**
 * Integrated Wellness Solution v2 — resolve + 3-domain render (B-track, human_confirm on clinician).
 */
import { NextRequest, NextResponse } from "next/server";

import type { PatientConsultInputV1 } from "@/lib/cdss-contract";
import { validateLaneABirth } from "@/lib/global-birth-input";
import {
  clinicianDevUnlock,
  clinicianEmailFromRequest,
  clinicianProEnforceGate,
  resolveClinicianProAccess,
} from "@/lib/clinician-access-server-v1";
import { runIntegratedWellnessPublishChain } from "@/lib/integrated-wellness-python-bridge-v1";

type IntegratedWellnessV2Request = {
  schema?: "integrated_wellness_v2_request_v1";
  request_id: string;
  patient_consult?: PatientConsultInputV1;
  sasang_candidate?: string;
  publish_personadiary?: boolean;
  publish_no1kmedi_static?: boolean;
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validateConsult(body: PatientConsultInputV1): string | null {
  if (body.schema !== "patient_consult_input_v1") return "invalid_schema";
  if (!isNonEmptyString(body.request_id)) return "missing_request_id";
  return validateLaneABirth(body.lane_a_profile || {});
}

export async function POST(request: NextRequest) {
  try {
    if (clinicianProEnforceGate() && !clinicianDevUnlock()) {
      const email = clinicianEmailFromRequest(request);
      if (!email) {
        return NextResponse.json(
          { success: false, error: "pro_clinical_assist_email_required" },
          { status: 403 },
        );
      }
      const access = await resolveClinicianProAccess(email);
      if (!access.unlocked) {
        return NextResponse.json(
          { success: false, error: "pro_clinical_assist_required" },
          { status: 403 },
        );
      }
    }

    const body = (await request.json()) as IntegratedWellnessV2Request;
    if (!isNonEmptyString(body.request_id)) {
      return NextResponse.json({ success: false, error: "missing_request_id" }, { status: 400 });
    }

    if (body.patient_consult) {
      const invalid = validateConsult(body.patient_consult);
      if (invalid) {
        return NextResponse.json({ success: false, error: invalid }, { status: 400 });
      }
    }

    const chain = runIntegratedWellnessPublishChain({
      requestId: body.request_id,
      consult: body.patient_consult,
      sasangCandidate: body.sasang_candidate,
      publishToNo1kmediPublic: body.publish_no1kmedi_static !== false,
      publishToPersonadiaryPublic: body.publish_personadiary !== false,
    });

    if (!chain.ok) {
      return NextResponse.json(
        { success: false, error: chain.error, stderr: chain.stderr },
        { status: 503 },
      );
    }

    return NextResponse.json(
      {
        success: true,
        track: "research_wellness_b",
        hypothesis_tier: "B",
        guardrail: {
          physician_confirmation_required: true,
          no_auto_trading_or_live_clinical_gating: true,
          no_spot_reduction_claims: true,
        },
        integrated_wellness: {
          out_dir: chain.outDir,
          resolved_path: chain.resolvedPath,
          no1kmedi_lifestyle_draft: chain.no1kmediDraft,
          personadiary_package_path: chain.personadiaryPackagePath,
          mkmlife_markdown_path: chain.mkmlifeMarkdownPath,
          manifest: chain.manifest,
        },
      },
      { status: 200, headers: { "Cache-Control": "no-store, no-cache, must-revalidate" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown";
    return NextResponse.json(
      { success: false, error: `integrated_wellness_v2_failed: ${message}` },
      { status: 500 },
    );
  }
}
