import { NextRequest, NextResponse } from "next/server";
import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";

type LeadBody = {
  email: string;
  name?: string;
  organization?: string;
  tier?: string;
  note?: string;
  source?: string;
};

function isNonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validate(body: LeadBody): string | null {
  if (!isNonEmpty(body.email)) return "email_required";
  if (!body.email.includes("@")) return "email_invalid";
  return null;
}

async function persistLead(row: Record<string, unknown>) {
  const dataDir =
    process.env.LOGOS_RESEARCH_LEAD_DATA_DIR?.trim() || path.join(process.cwd(), ".data");
  await mkdir(dataDir, { recursive: true });
  const file = path.join(dataDir, "logos_research_pilot_leads_v1.jsonl");
  await appendFile(file, `${JSON.stringify(row)}\n`, "utf8");
  return file;
}

async function sendWebhook(url: string, payload: Record<string, unknown>) {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    return { delivered: response.ok, status: response.status };
  } catch (error: unknown) {
    return {
      delivered: false,
      error: error instanceof Error ? error.message : "webhook_failed",
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as LeadBody;
    const invalid = validate(body);
    if (invalid) {
      return NextResponse.json({ ok: false, error: invalid }, { status: 400 });
    }

    const normalized = {
      lead_id: `lr_lead_${Date.now()}`,
      ts_utc: new Date().toISOString(),
      source: (body.source || "logos-research-studio-v1").trim(),
      email: body.email.trim().toLowerCase(),
      name: (body.name || "").trim(),
      organization: (body.organization || "").trim(),
      tier: (body.tier || "pilot").trim(),
      note: (body.note || "").trim(),
      host: request.headers.get("host") || "",
      research_only: true,
      send_gate: "HOLD",
    };

    const storedAt = await persistLead(normalized);
    const webhookUrl = process.env.LOGOS_RESEARCH_LEAD_WEBHOOK_URL?.trim();
    const webhook = webhookUrl
      ? { enabled: true, ...(await sendWebhook(webhookUrl, normalized)) }
      : { enabled: false, delivered: false };

    console.log("[logos-research-lead]", JSON.stringify({ ...normalized, stored_at: storedAt }));

    return NextResponse.json(
      { ok: true, lead_id: normalized.lead_id, webhook },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
