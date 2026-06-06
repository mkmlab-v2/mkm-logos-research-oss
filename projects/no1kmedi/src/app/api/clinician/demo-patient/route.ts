/**
 * Load SSOT demo patient context for /clinician (park_geumja etc.).
 */
import fs from "node:fs";
import path from "node:path";

import { NextRequest, NextResponse } from "next/server";

import { clinicianProUnlocked } from "@/lib/clinician-access-server-v1";
import { loadPatientPointer } from "@/lib/clinician-patient-slug-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export const runtime = "nodejs";

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
}

export async function GET(request: NextRequest) {
  if (!clinicianProUnlocked(request)) return unauthorized();

  const slug = (request.nextUrl.searchParams.get("slug") || "park_geumja").trim();
  const root = resolveMkmWorkspaceRoot();
  if (!root) {
    return NextResponse.json({ success: false, error: "workspace_root_not_found" }, { status: 503 });
  }

  const pointer = loadPatientPointer(root, slug);
  if (!pointer) {
    return NextResponse.json({ success: false, error: `unknown_slug:${slug}` }, { status: 404 });
  }

  const intakeRel = pointer.paths?.intake;
  const intakePath = intakeRel ? path.join(root, intakeRel) : null;
  let intake: Record<string, unknown> | null = null;
  if (intakePath && fs.existsSync(intakePath)) {
    try {
      intake = JSON.parse(fs.readFileSync(intakePath, "utf-8")) as Record<string, unknown>;
    } catch {
      intake = null;
    }
  }

  const profile = (intake?.profile || {}) as Record<string, unknown>;
  const intakeBlock = (intake?.intake || {}) as Record<string, unknown>;
  const symptoms = Array.isArray(intakeBlock.symptoms) ? intakeBlock.symptoms.map(String) : [];
  const chief = symptoms.slice(0, 3).join(" · ") || "만성 복합 증상";

  return NextResponse.json({
    success: true,
    slug,
    display_label: pointer.display_label,
    ref_token: pointer.ref_token,
    context_patch: {
      ssotSlug: slug,
      birthInstantUtc: String(profile.birth_instant_utc || ""),
      ianaTz: String(profile.iana_tz || "Asia/Seoul"),
      chiefComplaint: chief,
      onset: "만성",
      severity: "중등도",
      digestionPattern: "때때로 불편",
      sleepPattern: "미기재",
      redFlagNotes: String(intakeBlock.medications_note || ""),
      loadedSurveyContext: {
        surveyId: `demo_${slug}`,
        intakePin: String(pointer.ref_token || slug).slice(0, 24),
        patientName: String(pointer.display_label || slug),
        triageLevel: "priority" as const,
      },
    },
    paths: pointer.paths,
    boundary: "데모 SSOT 환자 — 임상 확정은 원장 권한.",
  });
}
