export type LeadWebhookDeliveryResult = {
  enabled: boolean;
  delivered: boolean;
  attempts?: number;
  error?: string;
  target?: "dedicated" | "fallback";
};

export function resolveLeadWebhookUrl(
  ...candidates: Array<string | undefined>
): { url: string; target: "dedicated" | "fallback" } | null {
  const [primary, ...fallbacks] = candidates;
  const primaryUrl = (primary || "").trim();
  if (primaryUrl) return { url: primaryUrl, target: "dedicated" };
  for (const fb of fallbacks) {
    const url = (fb || "").trim();
    if (url) return { url, target: "fallback" };
  }
  return null;
}

export function formatSlackLeadWebhookBody(
  headline: string,
  payload: Record<string, unknown>,
): Record<string, unknown> {
  return {
    text: headline,
    payload,
  };
}

export async function deliverLeadWebhook(
  url: string,
  payload: Record<string, unknown>,
  options?: { slackHeadline?: string; retries?: number },
): Promise<LeadWebhookDeliveryResult> {
  const target = url.trim();
  if (!target) return { enabled: false, delivered: false };

  const retries = options?.retries ?? 2;
  const isSlack = target.includes("hooks.slack.com/services/");
  const body =
    isSlack && options?.slackHeadline
      ? formatSlackLeadWebhookBody(options.slackHeadline, payload)
      : payload;

  let lastError: string | null = null;
  for (let attempt = 1; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(target, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        cache: "no-store",
      });
      if (response.ok) {
        return { enabled: true, delivered: true, attempts: attempt };
      }
      lastError = `webhook_http_${response.status}`;
    } catch (error: unknown) {
      lastError = error instanceof Error ? error.message : "unknown_webhook_error";
    }
    if (attempt < retries) {
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }

  return {
    enabled: true,
    delivered: false,
    attempts: retries,
    error: lastError || "webhook_failed",
  };
}
