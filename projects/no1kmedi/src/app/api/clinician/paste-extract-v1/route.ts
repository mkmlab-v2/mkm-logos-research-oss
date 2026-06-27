import { NextRequest, NextResponse } from "next/server";

import { clinicianProUnlocked } from "@/lib/clinician-access-server-v1";
import { extractPasteChartDraftLlmV1, pasteExtractLlmEnabled } from "@/lib/clinician-paste-extract-llm-v1";

export const runtime = "nodejs";

type Body = {
  chart_text?: string;
  intake_text?: string;
};

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "clinician_pro_required" }, { status: 401 });
}

export async function POST(request: NextRequest) {
  if (!clinicianProUnlocked(request)) return unauthorized();

  if (!pasteExtractLlmEnabled()) {
    return NextResponse.json(
      {
        success: false,
        error: "paste_extract_llm_disabled",
        hint: "Set KM_CLINICIAN_PASTE_EXTRACT_LLM=1 and configure GEMINI_API_KEY or CDSS LLM",
      },
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

  const result = await extractPasteChartDraftLlmV1(chartText);
  if (!result.ok) {
    const status = result.error === "paste_extract_llm_disabled" ? 503 : 422;
    return NextResponse.json(
      {
        success: false,
        error: result.error,
        regex_baseline: result.regex_baseline ?? null,
      },
      { status },
    );
  }

  return NextResponse.json({
    success: true,
    draft: result.draft,
    provider: result.provider,
    research_only: true,
    human_confirm_required: true,
    regex_baseline: result.regex_baseline,
  });
}
