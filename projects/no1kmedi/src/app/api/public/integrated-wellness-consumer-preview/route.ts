/**
 * Public B-track IWS consumer preview — mkmlife ask-one dynamic wellness (no Pro gate).
 */
import { NextRequest, NextResponse } from "next/server";

import type { PatientConsultInputV1 } from "@/lib/cdss-contract";
import {
  buildConsumerConsultFromPreview,
  corsHeadersForOrigin,
  type IntegratedWellnessConsumerPreviewRequest,
} from "@/lib/integrated-wellness-consumer-preview-v1";
import { runIntegratedWellnessPublishChain } from "@/lib/integrated-wellness-python-bridge-v1";

export async function OPTIONS(request: NextRequest) {
  const origin = request.headers.get("origin");
  return new NextResponse(null, {
    status: 204,
    headers: {
      ...corsHeadersForOrigin(origin),
      "Cache-Control": "no-store",
    },
  });
}

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  const cors = corsHeadersForOrigin(origin);

  try {
    const body = (await request.json()) as IntegratedWellnessConsumerPreviewRequest;
    const built = buildConsumerConsultFromPreview(body);
    if (!built.ok) {
      return NextResponse.json(
        { success: false, error: built.error },
        { status: 400, headers: { ...cors, "Cache-Control": "no-store" } },
      );
    }

    const consultWithGender = {
      ...built.consult,
      gender: body.gender || "unspecified",
    } as PatientConsultInputV1 & { gender?: string };

    const chain = runIntegratedWellnessPublishChain({
      requestId: body.request_id,
      consult: consultWithGender,
      sasangCandidate: built.sasangCandidate,
      publishToNo1kmediPublic: false,
      publishToPersonadiaryPublic: false,
      publishToMkmlifePublic: false,
    });

    if (!chain.ok) {
      return NextResponse.json(
        { success: false, error: chain.error, stderr: chain.stderr },
        { status: 503, headers: { ...cors, "Cache-Control": "no-store" } },
      );
    }

    if (!chain.mkmlifeRender) {
      return NextResponse.json(
        { success: false, error: "mkmlife_render_missing" },
        { status: 503, headers: { ...cors, "Cache-Control": "no-store" } },
      );
    }

    return NextResponse.json(
      {
        success: true,
        track: "research_wellness_b",
        hypothesis_tier: "B",
        non_gating: true,
        guardrail: {
          no_auto_trading_or_live_clinical_gating: true,
          no_spot_reduction_claims: true,
          physician_confirmation_not_applicable: true,
        },
        mkmlife_report: chain.mkmlifeRender,
      },
      { status: 200, headers: { ...cors, "Cache-Control": "no-store, no-cache, must-revalidate" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown";
    return NextResponse.json(
      { success: false, error: `consumer_preview_failed: ${message}` },
      { status: 500, headers: { ...cors, "Cache-Control": "no-store" } },
    );
  }
}
