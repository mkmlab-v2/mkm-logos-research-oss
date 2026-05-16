/**
 * Backoffice: validated CDS envelope (+ optional consult rebuild) → patient_care_bundle_v1 chain.
 * Requires MKM_WORKSPACE_ROOT. Physician-final; not patient-facing without review.
 */
import fs from "node:fs";

import { NextRequest, NextResponse } from "next/server";

import type { PatientConsultInputV1 } from "@/lib/cdss-contract";
import { buildAdvancedConsultDraft } from "@/lib/cdss-inference";
import { buildKmCdsEnvelopePipeline } from "@/lib/km-cds-envelope-pipeline-v1";
import { validateLaneABirth } from "@/lib/global-birth-input";
import {
  isPatientCareBundleTokenRequired,
  isPatientCareBundleTokenValid,
} from "@/lib/km-patient-care-bundle-auth-v1";
import {
  birthInstantToLocalParts,
  runPatientCareBundleFromCdsChain,
} from "@/lib/km-patient-care-bundle-python-bridge-v1";

type PatientCareBundleFromCdsRequestV1 = {
  schema: "patient_care_bundle_from_cds_request_v1";
  request_id: string;
  birth_instant_utc: string;
  iana_tz: string;
  is_male?: boolean;
  /** Pre-built envelope (e.g. from advanced-consult `km_cds.envelope`). */
  cds_envelope?: Record<string, unknown>;
  /** When envelope omitted, run CDSS then pipeline. */
  patient_consult?: PatientConsultInputV1;
  soap?: Record<string, unknown>;
  options?: {
    apply_slot_templates?: boolean;
    validate_policy?: boolean;
    validate_bundle?: boolean;
    render_patient_md?: boolean;
  };
};

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validateConsultInput(body: PatientConsultInputV1): string | null {
  if (body.schema !== "patient_consult_input_v1") return "invalid_patient_consult_schema";
  if (!isNonEmptyString(body.request_id)) return "missing_request_id";
  const birthErr = validateLaneABirth(body.lane_a_profile || {});
  if (birthErr) return birthErr;
  if (!isNonEmptyString(body.lane_b_clinical?.chief_complaint)) return "missing_chief_complaint";
  return null;
}

export async function POST(request: NextRequest) {
  if (isPatientCareBundleTokenRequired(request) && !isPatientCareBundleTokenValid(request)) {
    return unauthorized();
  }

  let body: PatientCareBundleFromCdsRequestV1;
  try {
    body = (await request.json()) as PatientCareBundleFromCdsRequestV1;
  } catch {
    return NextResponse.json({ success: false, error: "invalid_json" }, { status: 400 });
  }

  if (body.schema !== "patient_care_bundle_from_cds_request_v1") {
    return NextResponse.json({ success: false, error: "invalid_schema" }, { status: 400 });
  }
  if (!isNonEmptyString(body.request_id)) {
    return NextResponse.json({ success: false, error: "missing_request_id" }, { status: 400 });
  }
  const utc = body.birth_instant_utc?.trim();
  const tz = body.iana_tz?.trim();
  const birthErr = validateLaneABirth({ birth_instant_utc: utc, iana_tz: tz });
  if (birthErr) {
    return NextResponse.json({ success: false, error: birthErr }, { status: 400 });
  }

  let envelope = body.cds_envelope;
  let consultDraft;
  let kmCdsMeta: Record<string, unknown> | undefined;

  if (!envelope) {
    const consult = body.patient_consult;
    if (!consult) {
      return NextResponse.json(
        { success: false, error: "cds_envelope_or_patient_consult_required" },
        { status: 400 },
      );
    }
    const consultInvalid = validateConsultInput(consult);
    if (consultInvalid) {
      return NextResponse.json({ success: false, error: consultInvalid }, { status: 400 });
    }
    consultDraft = await buildAdvancedConsultDraft(consult);
    const pipeline = buildKmCdsEnvelopePipeline(consult, consultDraft);
    if (!pipeline.ok) {
      return NextResponse.json(
        { success: false, error: "km_cds_envelope_pipeline_failed", detail: pipeline.error },
        { status: 422 },
      );
    }
    envelope = pipeline.envelope;
    kmCdsMeta = { payload: pipeline.payload, tri_layer: pipeline.tri_layer };
  } else if (envelope.schema !== "km_physician_cds_assist_envelope_v1") {
    return NextResponse.json({ success: false, error: "invalid_cds_envelope_schema" }, { status: 400 });
  }

  const localBirth = birthInstantToLocalParts(utc!, tz!);
  const chain = runPatientCareBundleFromCdsChain({
    requestId: body.request_id,
    cdsEnvelope: envelope,
    birth: {
      year: localBirth.year,
      month: localBirth.month,
      day: localBirth.day,
      hour: localBirth.hour,
      minute: localBirth.minute,
      second: localBirth.second,
    },
    ianaTz: tz!,
    isMale: body.is_male === true,
    soapJson: body.soap,
    applySlotTemplates: body.options?.apply_slot_templates === true,
    validatePolicy: body.options?.validate_policy === true,
    validateBundle: body.options?.validate_bundle !== false,
    renderMdOut: body.options?.render_patient_md === true,
  });

  if (!chain.ok) {
    return NextResponse.json(
      { success: false, error: "patient_care_bundle_chain_failed", detail: chain.error },
      { status: 502 },
    );
  }

  let patientFacingMarkdown: string | undefined;
  if (chain.markdownPath && fs.existsSync(chain.markdownPath)) {
    try {
      patientFacingMarkdown = fs.readFileSync(chain.markdownPath, "utf-8");
    } catch {
      patientFacingMarkdown = undefined;
    }
  }

  return NextResponse.json(
    {
      success: true,
      request_id: body.request_id,
      consult_draft: consultDraft,
      km_cds: kmCdsMeta,
      patient_care_bundle: chain.bundle,
      patient_facing_markdown: patientFacingMarkdown,
      artifacts: {
        bundle_path: chain.bundlePath,
        myeongni_path: chain.myeongniPath,
        patient_facing_md_path: chain.markdownPath,
      },
      boundary: {
        physician_confirmation_required: true,
        not_standalone_diagnosis: true,
        research_only_myeongni_slots: true,
      },
    },
    { status: 200, headers: { "Cache-Control": "no-store" } },
  );
}
