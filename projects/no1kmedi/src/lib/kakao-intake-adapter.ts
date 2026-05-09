export type KakaoDeliveryResult = {
  enabled: boolean;
  delivered: boolean;
  status?: number;
  error?: string;
};

export async function deliverKakaoIntakeSummary(
  webhookUrl: string | undefined,
  summaryPayload: Record<string, unknown>,
): Promise<KakaoDeliveryResult> {
  const target = (webhookUrl || "").trim();
  if (!target) return { enabled: false, delivered: false };

  try {
    const isSlackStyle = target.includes("hooks.slack.com/services/");
    const body = isSlackStyle
      ? {
          text: `[clinic-intake] ${String(summaryPayload.receipt_id || "unknown_receipt")} / ${String(summaryPayload.triage_level || "unknown")}`,
          payload: summaryPayload,
        }
      : summaryPayload;

    const res = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    return { enabled: true, delivered: res.ok, status: res.status };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_webhook_error";
    return { enabled: true, delivered: false, error: message };
  }
}
