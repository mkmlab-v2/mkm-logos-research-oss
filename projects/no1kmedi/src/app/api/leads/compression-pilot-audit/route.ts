import { NextRequest, NextResponse } from "next/server";
import {
  normalizeCompressionPilotAuditApply,
  validateCompressionPilotAuditApply,
  type CompressionPilotAuditApplyPayload,
} from "@/lib/compressionPilotAuditApplyV1";
import { deliverLeadWebhook, resolveLeadWebhookUrl } from "@/lib/leadWebhookDeliveryV1";
import { verifyTurnstileToken } from "@/lib/turnstileServerV1";

function resolveCompressionPilotWebhook() {
  return resolveLeadWebhookUrl(
    process.env.COMPRESSION_PILOT_AUDIT_LEAD_WEBHOOK_URL,
    process.env.FREE_VALIDATION_LEAD_WEBHOOK_URL,
    process.env.OPS_ALARM_WEBHOOK_URL,
    process.env.SLACK_WEBHOOK_URL,
  );
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as CompressionPilotAuditApplyPayload;
    const turnstile = await verifyTurnstileToken(
      body.turnstile_token,
      request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || undefined,
      "compression-pilot-audit",
    );
    if (!turnstile.ok) {
      return NextResponse.json({ success: false, error: turnstile.error }, { status: 400 });
    }

    const invalid = validateCompressionPilotAuditApply(body);
    if (invalid) {
      return NextResponse.json({ success: false, error: invalid }, { status: 400 });
    }

    const applicationId = `cpa_${Date.now()}`;
    const normalized = normalizeCompressionPilotAuditApply(body, applicationId);

    const resolved = resolveCompressionPilotWebhook();
    let webhookDelivery: Record<string, unknown> = { enabled: false, delivered: false };
    if (resolved) {
      const delivery = await deliverLeadWebhook(resolved.url, normalized, {
        slackHeadline: `[compression-pilot-audit] ${applicationId} · ${normalized.company_legal_name} · ${normalized.contact_email} · ${normalized.primary_domain}`,
      });
      webhookDelivery = {
        ...delivery,
        target: resolved.target,
      };
    }

    console.log("[compression-pilot-audit-apply]", JSON.stringify(normalized));
    if (webhookDelivery.enabled && !webhookDelivery.delivered) {
      console.warn(
        "[compression-pilot-audit-webhook-failed]",
        JSON.stringify({ application_id: applicationId, webhookDelivery }),
      );
    }

    return NextResponse.json(
      { success: true, application_id: applicationId, webhook: webhookDelivery },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json(
      { success: false, error: `apply_submit_failed:${message}` },
      { status: 500 },
    );
  }
}
