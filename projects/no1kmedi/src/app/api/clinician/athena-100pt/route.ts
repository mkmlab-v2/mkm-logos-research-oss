/**
 * Build han_physician turn + athena_100_point_report on disk (MKM workspace Python).
 * Track B · physician-final · not patient-facing without review.
 */
import fs from "node:fs";
import path from "node:path";

import { NextRequest, NextResponse } from "next/server";

import { clinicianProUnlocked } from "@/lib/clinician-access-server-v1";
import {
  appendChatTranscriptToMd,
  runAthena100ptFromSlug,
} from "@/lib/km-athena-100pt-python-bridge-v1";
import { resolvePatientSlug } from "@/lib/clinician-patient-slug-v1";
import { resolveMkmWorkspaceRoot } from "@/lib/km-workspace-root-v1";

export const runtime = "nodejs";

type ChatTurn = { role: string; message: string };

type Body = {
  schema?: string;
  slug?: string;
  ref_token?: string;
  chat_transcript?: ChatTurn[];
  persist?: boolean;
  append_chat_to_md?: boolean;
};

function unauthorized(): NextResponse {
  return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
}

export async function POST(request: NextRequest) {
  if (!clinicianProUnlocked(request)) return unauthorized();

  const root = resolveMkmWorkspaceRoot();
  if (!root) {
    return NextResponse.json(
      { success: false, error: "workspace_root_not_found", hint: "Set MKM_WORKSPACE_ROOT to monorepo root" },
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

  const chain = runAthena100ptFromSlug(
    {
      slug: resolved.slug,
      validateSchema: true,
      updatePointer: body.persist !== false,
      writeLatest: body.persist !== false,
    },
    root,
  );

  if (!chain.ok) {
    return NextResponse.json({ success: false, error: chain.error, stderr: chain.stderr }, { status: 500 });
  }

  let md = chain.reportMdContent;
  const turns = Array.isArray(body.chat_transcript) ? body.chat_transcript : [];
  if (body.append_chat_to_md !== false && turns.length) {
    md = appendChatTranscriptToMd(md, turns);
    if (body.persist !== false) {
      fs.writeFileSync(chain.reportMd, `${md}\n`, "utf-8");
      const latest = path.join(root, "reports", `${resolved.slug}_athena_100pt_v1.latest.md`);
      fs.writeFileSync(latest, `${md}\n`, "utf-8");
    }
  }

  const rel = (abs: string) => path.relative(root, abs).replace(/\\/g, "/");

  return NextResponse.json({
    success: true,
    rail: "Track B",
    research_only: true,
    display_label: resolved.pointer.display_label,
    ref_token: resolved.pointer.ref_token,
    slug: resolved.slug,
    paths: {
      han_turn_json: rel(chain.hanTurnJson),
      han_turn_md: rel(chain.hanTurnMd),
      athena_100pt_json: rel(chain.reportJson),
      athena_100pt_md: rel(chain.reportMd),
    },
    markdown: md,
    boundary:
      "진단·처방 단정 금지. 본 산출은 원장 확정 전 보조 리포트이며 Track A·실매매와 합선되지 않습니다.",
  });
}
