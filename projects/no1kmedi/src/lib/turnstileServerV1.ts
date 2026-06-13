import {
  getTurnstileSecretKey,
  isTurnstileConfigured,
  shouldSkipTurnstileVerify,
} from "@/lib/turnstileConfigV1";

export type TurnstileVerifyResult =
  | { ok: true; skipped?: boolean }
  | { ok: false; error: string };

type SiteverifyResponse = {
  success?: boolean;
  "error-codes"?: string[];
};

/** Free-tier ops log (no token/secret/PII). Visible in host logs + Vercel/CF Workers stdout. */
export function logTurnstileVerifyEvent(event: {
  context: string;
  ok: boolean;
  skipped?: boolean;
  error?: string;
}) {
  console.log(
    "[turnstile-verify]",
    JSON.stringify({
      ts: new Date().toISOString(),
      context: event.context,
      ok: event.ok,
      skipped: Boolean(event.skipped),
      error: event.error ?? null,
    }),
  );
}

export async function verifyTurnstileToken(
  token: string | undefined,
  remoteIp?: string,
  context = "unknown",
): Promise<TurnstileVerifyResult> {
  if (shouldSkipTurnstileVerify()) {
    const result: TurnstileVerifyResult = { ok: true, skipped: true };
    logTurnstileVerifyEvent({ context, ...result });
    return result;
  }
  if (!isTurnstileConfigured()) {
    const result: TurnstileVerifyResult = { ok: true, skipped: true };
    logTurnstileVerifyEvent({ context, ...result });
    return result;
  }

  const trimmed = (token || "").trim();
  if (!trimmed) {
    const result: TurnstileVerifyResult = { ok: false, error: "turnstile_token_required" };
    logTurnstileVerifyEvent({ context, ...result });
    return result;
  }

  const body = new URLSearchParams({
    secret: getTurnstileSecretKey(),
    response: trimmed,
  });
  if (remoteIp) body.set("remoteip", remoteIp);

  const res = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });

  const json = (await res.json()) as SiteverifyResponse;
  if (json.success) {
    const result: TurnstileVerifyResult = { ok: true };
    logTurnstileVerifyEvent({ context, ...result });
    return result;
  }

  const codes = (json["error-codes"] || []).join(",");
  const result: TurnstileVerifyResult = {
    ok: false,
    error: codes ? `turnstile_verify_failed:${codes}` : "turnstile_verify_failed",
  };
  logTurnstileVerifyEvent({ context, ...result });
  return result;
}
