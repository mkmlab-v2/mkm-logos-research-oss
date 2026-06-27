/**
 * POST EMR/chart paste → SOAP (fusion) + 한의 조언 (copilot) — Paste Chart v1.
 * Track B · research_only · send_gate HOLD
 */
import { NextRequest, NextResponse } from "next/server";

import { clinicianProUnlocked } from "@/lib/clinician-access-server-v1";
import { runPasteChartV1Chain } from "@/lib/km-paste-chart-bridge-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export const runtime = "nodejs";

type Body = {
  schema?: string;
  slug?: string;
  ref_token?: string;
  display?: string;
  chart_text?: string;
  intake_text?: string;
  objective_draft?: string;
  birth_instant_utc?: string;
  iana_tz?: string;
  is_male?: boolean;
  sasang_label?: string;
  skip_advice?: boolean;
  allow_ephemeral?: boolean;
  options?: {
    validate_schema?: boolean;
    validate_policy?: boolean;
    render_md?: boolean;
    brief_output?: boolean;
  };
};

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
}

export async function POST(request: NextRequest) {
  if (!clinicianProUnlocked(request)) return unauthorized();

  const root = resolveMkmWorkspaceRoot();
  if (!root) {
    return NextResponse.json(
      { success: false, error: "workspace_root_not_found", hint: "Set MKM_WORKSPACE_ROOT" },
      { status: 503 },
    );
  }

  let body: Body;
  try {
    body = (await request.json()) as Body;
  } catch {
    return NextResponse.json({ success: false, error: "invalid_json" }, { status: 400 });
  }

  const chartText = String(body.chart_text || body.intake_text || "").trim();
  if (!chartText) {
    return NextResponse.json({ success: false, error: "chart_text_required" }, { status: 400 });
  }

  const opts = body.options || {};
  const result = await runPasteChartV1Chain(
    {
      slug: body.slug,
      refToken: body.ref_token,
      display: body.display,
      chartText,
      intakeText: chartText,
      objectiveDraft: body.objective_draft,
      birthInstantUtc: body.birth_instant_utc,
      ianaTz: body.iana_tz,
      isMale: body.is_male,
      sasangLabel: body.sasang_label,
      skipAdvice: body.skip_advice,
      allowEphemeral: body.allow_ephemeral !== false,
      validateSchema: opts.validate_schema,
      validatePolicy: opts.validate_policy,
      renderMd: opts.render_md,
      briefOutput: opts.brief_output,
    },
    root,
  );

  if (!result.ok) {
    const status = result.error.startsWith("unknown_") ? 404 : 500;
    return NextResponse.json(
      { success: false, error: result.error, stderr: result.stderr, advice_error: result.advice_error },
      { status },
    );
  }

  return NextResponse.json(
    {
      success: true,
      product: "paste_chart_v1",
      rail: "Track B",
      research_only: true,
      send_gate: "HOLD",
      slug: result.slug,
      display_label: result.displayLabel,
      ref_token: result.refToken,
      ephemeral: Boolean(result.ephemeral),
      paths: { bundle_json: result.bundlePath },
      patient_care_bundle: result.bundle,
      clinical_soap_v1: result.soap,
      patient_facing_markdown: result.patientFacingMarkdown,
      advice: result.advice,
      advice_error: result.advice_error,
      boundary:
        "EMR paste → SOAP + 조언 초안. 진단·처방·EMR 자동기록 없음. 원장 Human Gold 확정 후 슬롯 복사만.",
    },
    { status: 200, headers: { "Cache-Control": "no-store, no-cache, must-revalidate" } },
  );
}
