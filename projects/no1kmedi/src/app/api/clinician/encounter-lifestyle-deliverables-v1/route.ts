/**
 * POST regenerate lifestyle print HTML (+ optional kakao draft from fusion MD).
 * physician_gold · does not overwrite clinic_kakao SSOT without Human Gold.
 */
import { NextRequest, NextResponse } from "next/server";

import { clinicianProUnlocked } from "@/lib/clinician-access-server-v1";
import { runEncounterLifestyleDeliverablesChain } from "@/lib/km-encounter-lifestyle-deliverables-bridge-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export const runtime = "nodejs";

type Body = {
  schema?: string;
  slug?: string;
  ref_token?: string;
  display?: string;
  fusion_markdown?: string;
  write_kakao_draft?: boolean;
};

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
}

export async function POST(request: NextRequest) {
  if (!clinicianProUnlocked(request)) return unauthorized();

  const root = resolveMkmWorkspaceRoot();
  if (!root) {
    return NextResponse.json({ success: false, error: "workspace_root_not_found" }, { status: 503 });
  }

  let body: Body;
  try {
    body = (await request.json()) as Body;
  } catch {
    return NextResponse.json({ success: false, error: "invalid_json" }, { status: 400 });
  }

  const result = runEncounterLifestyleDeliverablesChain(
    {
      slug: body.slug,
      refToken: body.ref_token,
      display: body.display,
      fusionMarkdown: body.fusion_markdown,
      writeKakaoDraft: body.write_kakao_draft,
    },
    root,
  );

  if (!result.ok) {
    const status = result.error.includes("unknown_") ? 404 : 500;
    return NextResponse.json({ success: false, error: result.error, stderr: result.stderr }, { status });
  }

  return NextResponse.json({
    success: true,
    rail: "Track B",
    research_only: true,
    send_gate: "HOLD",
    slug: result.slug,
    display_label: result.displayLabel,
    ref_token: result.refToken,
    paths: {
      lifestyle_json: result.lifestyleJsonRel,
      print_html: result.printHtmlRel,
      kakao_draft: result.kakaoDraftRel,
      kakao_gold: result.kakaoGoldRel,
    },
    boundary:
      "인쇄 HTML 재생성만 자동. 카톡 gold SSOT는 덮어쓰지 않음 — fusion 드래프트는 cdss_runtime에만.",
    reproducible_command: `py scripts/render_clinic_lifestyle_management_print_v1.py --input-json ${result.lifestyleJsonRel} --out-html ${result.printHtmlRel}`,
  });
}
