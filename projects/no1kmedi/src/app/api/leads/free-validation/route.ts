/**
 * @MKM12-METADATA
 * Type: Engine
 * Vector: {S:0.82, L:0.74, K:0.71, M:0.57}
 * Balance: 91
 * Purpose: Receive and normalize free validation lead submissions.
 * Keywords: Next.js, API, lead, validation, conversion
 */
import { NextRequest, NextResponse } from "next/server";

type FreeValidationLead = {
  name: string;
  email: string;
  company: string;
  use_case?: string;
};

function isNonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validate(body: FreeValidationLead): string | null {
  if (!isNonEmpty(body.name)) return "name_required";
  if (!isNonEmpty(body.email)) return "email_required";
  if (!body.email.includes("@")) return "email_invalid";
  if (!isNonEmpty(body.company)) return "company_required";
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

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as FreeValidationLead;
    const invalid = validate(body);
    if (invalid) {
      return NextResponse.json({ success: false, error: invalid }, { status: 400 });
    }

    const normalized = {
      lead_id: `lead_${Date.now()}`,
      ts_utc: new Date().toISOString(),
      source: "a-codeai-home-free-validation",
      name: body.name.trim(),
      email: body.email.trim().toLowerCase(),
      company: body.company.trim(),
      use_case: (body.use_case || "").trim(),
    };

    const webhookUrl = process.env.FREE_VALIDATION_LEAD_WEBHOOK_URL;
    let webhookDelivery: Record<string, unknown> = {
      enabled: false,
      delivered: false,
    };
    if (webhookUrl) {
      webhookDelivery = {
        enabled: true,
        ...(await sendWebhookWithRetry(webhookUrl, normalized)),
      };
    }

    console.log("[free-validation-lead]", JSON.stringify(normalized));
    if (webhookDelivery.enabled && !webhookDelivery.delivered) {
      console.warn("[free-validation-lead-webhook-failed]", JSON.stringify({ lead_id: normalized.lead_id, webhookDelivery }));
    }

    return NextResponse.json(
      { success: true, lead_id: normalized.lead_id, webhook: webhookDelivery },
      { status: 200, headers: { "Cache-Control": "no-store" } }
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ success: false, error: `lead_submit_failed:${message}` }, { status: 500 });
  }
}
