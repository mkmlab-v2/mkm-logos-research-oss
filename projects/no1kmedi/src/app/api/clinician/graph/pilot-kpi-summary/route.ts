import { NextResponse } from "next/server";
import { promises as fs } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";

const ARTIFACT_CANDIDATES = [
  path.join(process.cwd(), "..", "..", "docs", "final", "artifacts", "clinician_graph_pilot_kpi_latest.json"),
  path.join(process.cwd(), "docs", "final", "artifacts", "clinician_graph_pilot_kpi_latest.json"),
];

const FEEDBACK_CANDIDATES = [
  path.join(process.cwd(), "reports", "clinician_graph_review_feedback_v1.jsonl"),
  path.join(process.cwd(), "..", "..", "reports", "clinician_graph_review_feedback_v1.jsonl"),
];

async function firstExisting(paths: string[]): Promise<string | null> {
  for (const p of paths) {
    try {
      await fs.access(p);
      return p;
    } catch {
      // continue
    }
  }
  return null;
}

async function readJsonIfExists(filePath: string | null) {
  if (!filePath) return null;
  try {
    const raw = await fs.readFile(filePath, "utf8");
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return null;
  }
}

async function countFeedbackLines(filePath: string | null) {
  if (!filePath) return 0;
  try {
    const raw = await fs.readFile(filePath, "utf8");
    return raw.split("\n").filter((line) => line.trim()).length;
  } catch {
    return 0;
  }
}

export async function GET() {
  const artifactPath = await firstExisting(ARTIFACT_CANDIDATES);
  const artifact = await readJsonIfExists(artifactPath);
  const feedbackPath = await firstExisting(FEEDBACK_CANDIDATES);
  const feedbackLines = await countFeedbackLines(feedbackPath);

  if (artifact) {
    return NextResponse.json(
      {
        success: true,
        source: "artifact",
        artifact_path: artifactPath,
        feedback_log_path: feedbackPath,
        feedback_line_count: feedbackLines,
        summary: artifact,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  }

  return NextResponse.json(
    {
      success: true,
      source: "inline_stub",
      artifact_path: null,
      feedback_log_path: feedbackPath,
      feedback_line_count: feedbackLines,
      summary: {
        schema: "clinician_graph_pilot_kpi_summary_v1",
        research_only: true,
        send_gate: "HOLD",
        kpi_headline: {
          physician_approval_rate: null,
          signoff_events: 0,
          conflict_reviews: 0,
          unique_encounters: 0,
          graph_build_events: 0,
          median_review_ms: null,
        },
        note: "Run py scripts/build_clinician_graph_pilot_kpi_report_v1.py to refresh artifact.",
      },
      boundary: {
        physician_confirmation_required: true,
        internal_pilot_only: true,
      },
    },
    { status: 200, headers: { "Cache-Control": "no-store" } },
  );
}
