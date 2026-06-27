import fs from "node:fs";
import path from "node:path";

import { NextRequest, NextResponse } from "next/server";

type FeedbackBody = {
  schema: "clinician_graph_review_feedback_request_v1";
  encounter_ref: string;
  target_id: string;
  target_kind: "node" | "edge";
  feedback: "up" | "down" | "hold";
  reason_code?: string;
  clinician_note?: string;
};

function clean(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

const FEEDBACK_LOG = path.join(process.cwd(), "reports", "clinician_graph_review_feedback_v1.jsonl");

export async function POST(request: NextRequest) {
  let body: FeedbackBody;
  try {
    body = (await request.json()) as FeedbackBody;
  } catch {
    return NextResponse.json({ success: false, error: "invalid_json" }, { status: 400 });
  }

  if (body.schema !== "clinician_graph_review_feedback_request_v1") {
    return NextResponse.json({ success: false, error: "invalid_schema" }, { status: 400 });
  }
  if (!clean(body.encounter_ref)) {
    return NextResponse.json({ success: false, error: "missing_encounter_ref" }, { status: 400 });
  }
  if (!clean(body.target_id)) {
    return NextResponse.json({ success: false, error: "missing_target_id" }, { status: 400 });
  }
  if (!["node", "edge"].includes(body.target_kind)) {
    return NextResponse.json({ success: false, error: "invalid_target_kind" }, { status: 400 });
  }
  if (!["up", "down", "hold"].includes(body.feedback)) {
    return NextResponse.json({ success: false, error: "invalid_feedback" }, { status: 400 });
  }

  const event = {
    schema: "clinician_graph_review_feedback_event_v1",
    ts: new Date().toISOString(),
    encounter_ref: clean(body.encounter_ref),
    target_id: clean(body.target_id),
    target_kind: body.target_kind,
    feedback: body.feedback,
    reason_code: clean(body.reason_code) || null,
    clinician_note: clean(body.clinician_note) || null,
    queued_for_review: true,
    auto_model_apply: false,
  };

  fs.mkdirSync(path.dirname(FEEDBACK_LOG), { recursive: true });
  fs.appendFileSync(FEEDBACK_LOG, `${JSON.stringify(event)}\n`, "utf-8");

  return NextResponse.json(
    {
      success: true,
      accepted: true,
      queued_for_review: true,
      next_revision_token: `rev_${Date.now()}`,
      boundary: {
        no_immediate_model_mutation: true,
        physician_confirmation_required: true,
      },
    },
    { status: 200, headers: { "Cache-Control": "no-store" } },
  );
}

