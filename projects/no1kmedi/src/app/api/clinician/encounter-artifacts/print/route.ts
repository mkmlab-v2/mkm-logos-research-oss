/**
 * Stream lifestyle print HTML for an encounter (opens in browser for 인쇄).
 */
import { NextRequest, NextResponse } from "next/server";

import { clinicianProUnlocked } from "@/lib/clinician-access-server-v1";
import { readEncounterPrintHtml } from "@/lib/clinician-encounter-artifacts-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export const runtime = "nodejs";

function unauthorized(): NextResponse {
  return new NextResponse("unauthorized", { status: 401 });
}

export async function GET(request: NextRequest) {
  if (!clinicianProUnlocked(request)) return unauthorized();

  const root = resolveMkmWorkspaceRoot();
  if (!root) return new NextResponse("workspace_root_not_found", { status: 503 });

  const slug = (request.nextUrl.searchParams.get("slug") || "").trim();
  if (!slug) return new NextResponse("slug_required", { status: 400 });

  const result = readEncounterPrintHtml(root, slug);
  if ("error" in result) return new NextResponse(result.error, { status: 404 });

  return new NextResponse(result.html, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
