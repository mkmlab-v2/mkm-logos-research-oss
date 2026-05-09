import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";

const DATA_DIR = path.join(process.cwd(), "memory", "commercialization");
const EVENTS_JSONL = path.join(DATA_DIR, "hub_events.jsonl");

type TelemetryPayload = {
  event?: string;
  session_id?: string;
  page_path?: string;
  source_surface?: string;
  target_surface?: string;
  target_href?: string;
  requested_level?: string;
  effective_level?: string;
  access_gate?: string;
  response_len?: number;
  [k: string]: unknown;
};

function sanitize(payload: TelemetryPayload) {
  const safe = {
    event: String(payload.event || "").slice(0, 80),
    session_id: String(payload.session_id || "").slice(0, 120),
    page_path: String(payload.page_path || "").slice(0, 200),
    source_surface: String(payload.source_surface || "").slice(0, 80),
    target_surface: String(payload.target_surface || "").slice(0, 80),
    target_href: String(payload.target_href || "").slice(0, 300),
    requested_level: String(payload.requested_level || "").slice(0, 40),
    effective_level: String(payload.effective_level || "").slice(0, 40),
    access_gate: String(payload.access_gate || "").slice(0, 80),
    response_len: Number.isFinite(Number(payload.response_len))
      ? Math.max(0, Math.min(20000, Number(payload.response_len)))
      : 0,
  };
  return safe;
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as TelemetryPayload;
    const normalized = sanitize(body);
    if (!normalized.event) {
      return NextResponse.json({ success: false, error: "event_required" }, { status: 400 });
    }

    await fs.mkdir(DATA_DIR, { recursive: true });
    const row = JSON.stringify({
      ...normalized,
      ts_utc: new Date().toISOString(),
      ua: request.headers.get("user-agent") || "",
    });
    await fs.appendFile(EVENTS_JSONL, row + "\n", "utf8");

    return NextResponse.json({ success: true }, { status: 200, headers: { "Cache-Control": "no-store" } });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ success: false, error: `telemetry_write_failed:${message}` }, { status: 500 });
  }
}
