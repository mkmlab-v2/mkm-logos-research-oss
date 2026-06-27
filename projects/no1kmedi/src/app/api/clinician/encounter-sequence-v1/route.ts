/**
 * Intake fusion → encounter_sequence → han physician turn (MKM workspace Python).
 * Track B · research_only · send_gate HOLD
 */
import { NextRequest, NextResponse } from "next/server";

import { clinicianProUnlocked } from "@/lib/clinician-access-server-v1";
import { resolvePatientSlug } from "@/lib/clinician-patient-slug-v1";
import { runEncounterSequenceClinicianChain } from "@/lib/km-encounter-sequence-python-bridge-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export const runtime = "nodejs";

type Body = {
  schema?: string;
  slug?: string;
  ref_token?: string;
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

  const slugHint =
    (body.slug || "").trim() ||
    (clinicianProUnlocked(request) && !(body.ref_token || "").trim() ? "park_geumja" : "");

  const resolved = resolvePatientSlug({
    slug: slugHint || undefined,
    refToken: body.ref_token,
    workspaceRoot: root,
  });
  if ("error" in resolved) {
    return NextResponse.json({ success: false, error: resolved.error }, { status: 400 });
  }

  const chain = runEncounterSequenceClinicianChain({ slug: resolved.slug }, root);
  if (!chain.ok) {
    return NextResponse.json({ success: false, error: chain.error, stderr: chain.stderr }, { status: 500 });
  }

  return NextResponse.json({
    success: true,
    rail: "Track B",
    research_only: true,
    send_gate: "HOLD",
    display_label: resolved.pointer.display_label,
    ref_token: chain.refToken || resolved.pointer.ref_token,
    slug: resolved.slug,
    encounter_sequence_id: chain.encounterSequenceId,
    paths: {
      sequence_json: chain.sequencePath,
      bundle_json: chain.bundlePath,
      han_turn_json: chain.hanTurnPath,
    },
    l0_router_triggered: chain.l0RouterTriggered,
    boundary:
      "진단·처방·응급 자동발송 없음. encounter_sequence는 AI 가설 참고용이며 원장 최종 판단 전 보조입니다.",
  });
}
