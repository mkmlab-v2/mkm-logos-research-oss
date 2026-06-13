export function getTurnstileSitekey(): string {
  return (process.env.NEXT_PUBLIC_TURNSTILE_SITEKEY || "").trim();
}

export function getTurnstileSecretKey(): string {
  return (process.env.TURNSTILE_SECRET_KEY || "").trim();
}

export function isTurnstileConfigured(): boolean {
  return Boolean(getTurnstileSitekey() && getTurnstileSecretKey());
}

/** Dev-only: set KM_TURNSTILE_SKIP_VERIFY=1 in .env.local (never production). */
export function shouldSkipTurnstileVerify(): boolean {
  return (
    process.env.KM_TURNSTILE_SKIP_VERIFY === "1" && process.env.NODE_ENV !== "production"
  );
}

export function isTurnstileClientEnabled(): boolean {
  return Boolean(getTurnstileSitekey());
}
