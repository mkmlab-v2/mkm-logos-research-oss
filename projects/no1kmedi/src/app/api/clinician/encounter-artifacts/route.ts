/**
 * GET encounter SSOT pointer + lifestyle/kakao markdown artifacts (Human Gold v0).
 * Local workspace only — PHI does not leave MKM_WORKSPACE_ROOT.
 */
import { NextRequest, NextResponse } from "next/server";

import { clinicianProUnlocked } from "@/lib/clinician-access-server-v1";
import {
  loadEncounterArtifacts,
  resolveEncounterPatient,
} from "@/lib/clinician-encounter-artifacts-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export const runtime = "nodejs";

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
}

export async function GET(request: NextRequest) {
  if (!clinicianProUnlocked(request)) return unauthorized();

  const root = resolveMkmWorkspaceRoot();
  if (!root) {
    return NextResponse.json(
      { success: false, error: "workspace_root_not_found", hint: "Set MKM_WORKSPACE_ROOT" },
      { status: 503 },
    );
  }

  const sp = request.nextUrl.searchParams;
  const resolved = resolveEncounterPatient({
    root,
    slug: sp.get("slug") || undefined,
    refToken: sp.get("ref_token") || undefined,
    display: sp.get("display") || undefined,
  });
  if ("error" in resolved) {
    return NextResponse.json({ success: false, error: resolved.error }, { status: 404 });
  }

  const includeContent = (sp.get("include_content") || "1").trim() !== "0";
  const payload = loadEncounterArtifacts({
    root,
    slug: resolved.slug,
    pointer: resolved.pointer,
    includeContent,
  });

  return NextResponse.json(payload);
}
