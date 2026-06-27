import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";

const DATA_DIR = path.join(process.cwd(), "memory", "commercialization");
const FEEDBACK_JSONL = path.join(DATA_DIR, "logos_studio_evidence_feedback_v1.jsonl");

type FeedbackBody = {
  verdict?: "up" | "down";
  issue_type?: "translation" | "context" | "source" | "other";
  preset_id?: string;
  query?: string;
  evidence_anchor?: string;
  note?: string;
};

function normText(value: unknown, max: number): string {
  return String(value || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, max);
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as FeedbackBody;
    const verdict = body.verdict === "up" || body.verdict === "down" ? body.verdict : "";
    const issueType =
      body.issue_type === "translation" ||
      body.issue_type === "context" ||
      body.issue_type === "source" ||
      body.issue_type === "other"
        ? body.issue_type
        : "";
    if (!verdict) {
      return NextResponse.json({ ok: false, error: "verdict_required" }, { status: 400 });
    }

    await fs.mkdir(DATA_DIR, { recursive: true });
    const row = JSON.stringify({
      schema: "logos_studio_evidence_feedback_v1",
      ts_utc: new Date().toISOString(),
      verdict,
      issue_type: verdict === "down" ? issueType || "other" : "",
      preset_id: normText(body.preset_id, 120),
      query: normText(body.query, 400),
      evidence_anchor: normText(body.evidence_anchor, 300),
      note: normText(body.note, 500),
      ua: request.headers.get("user-agent") || "",
      research_only: true,
      send_gate: "HOLD",
      non_gating: true,
    });
    await fs.appendFile(FEEDBACK_JSONL, row + "\n", "utf8");
    return NextResponse.json(
      { ok: true, schema: "logos_studio_evidence_feedback_ack_v1" },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: `feedback_write_failed:${message}` }, { status: 500 });
  }
}

