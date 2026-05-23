/**
 * @MKM12-METADATA
 * Type: Engine
 * Purpose: personadiary open-beta waitlist (preview_only, append-only JSONL).
 */
import { NextRequest, NextResponse } from "next/server";
import { appendFile, mkdir } from "fs/promises";
import path from "path";

type WaitlistBody = {
  email: string;
  name?: string;
  note?: string;
};

function isNonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validate(body: WaitlistBody): string | null {
  if (!isNonEmpty(body.email)) return "email_required";
  if (!body.email.includes("@")) return "email_invalid";
  return null;
}

async function sendWebhookWithRetry(url: string, payload: Record<string, unknown>) {
  let lastError: string | null = null;
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      });
      if (response.ok) return { delivered: true, attempts: attempt };
      lastError = `webhook_http_${response.status}`;
    } catch (error: unknown) {
      lastError = error instanceof Error ? error.message : "unknown_webhook_error";
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return { delivered: false, attempts: 2, error: lastError || "webhook_failed" };
}

async function persistLead(row: Record<string, unknown>) {
  const dataDir =
    process.env.PERSONADIARY_WAITLIST_DATA_DIR?.trim() ||
    path.join(process.cwd(), ".data");
  await mkdir(dataDir, { recursive: true });
  const file = path.join(dataDir, "personadiary_waitlist_leads_v1.jsonl");
  await appendFile(file, `${JSON.stringify(row)}\n`, "utf8");
  return file;
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as WaitlistBody;
    const invalid = validate(body);
    if (invalid) {
      return NextResponse.json({ success: false, error: invalid }, { status: 400 });
    }

    const normalized = {
      lead_id: `pd_wait_${Date.now()}`,
      ts_utc: new Date().toISOString(),
      source: "personadiary-waitlist-v1",
      email: body.email.trim().toLowerCase(),
      name: (body.name || "").trim(),
      note: (body.note || "").trim(),
      host: request.headers.get("host") || "",
    };

    const storedAt = await persistLead(normalized);

    const webhookUrl = process.env.PERSONADIARY_WAITLIST_WEBHOOK_URL?.trim();
    let webhookDelivery: Record<string, unknown> = { enabled: false, delivered: false };
    if (webhookUrl) {
      webhookDelivery = {
        enabled: true,
        ...(await sendWebhookWithRetry(webhookUrl, normalized)),
      };
    }

    console.log("[personadiary-waitlist]", JSON.stringify({ ...normalized, stored_at: storedAt }));

    return NextResponse.json(
      {
        success: true,
        lead_id: normalized.lead_id,
        webhook: webhookDelivery,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } }
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json(
      { success: false, error: `waitlist_submit_failed:${message}` },
      { status: 500 }
    );
  }
}
