import type { NextRequest, NextResponse } from "next/server";

export const LOGOS_FREE_DAILY_QUOTA = 8;
export const LOGOS_QUOTA_COOKIE = "lr_q_v1";

function isTruthyEnv(value: string | undefined): boolean {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

/** Dev/commander: LOGOS_STUDIO_QUOTA_DISABLED=1 — skip cookie quota (research_only showroom). */
export function isLogosStudioQuotaDisabled(): boolean {
  return isTruthyEnv(process.env.LOGOS_STUDIO_QUOTA_DISABLED);
}

/** Hero iframe / demo=1 — quota-free, preset allowlist only */
export const LOGOS_EMBED_DEMO_PRESET_ALLOWLIST = new Set([
  "job_job_suffering_reason",
  "isaiah_youtube_spine_v1",
  "bigset_topic_nephilim",
  "topic_ezra_1_anchor",
]);

export function isEmbedDemoPreset(presetId: string): boolean {
  return LOGOS_EMBED_DEMO_PRESET_ALLOWLIST.has(presetId);
}

type QuotaCookie = {
  d: string;
  n: number;
};

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

function parseQuotaCookie(raw: string | undefined): QuotaCookie {
  const day = todayUtc();
  if (!raw) return { d: day, n: 0 };
  try {
    const decoded = Buffer.from(raw, "base64url").toString("utf8");
    const parsed = JSON.parse(decoded) as QuotaCookie;
    if (parsed.d !== day) return { d: day, n: 0 };
    return { d: day, n: Number(parsed.n) || 0 };
  } catch {
    return { d: day, n: 0 };
  }
}

function encodeQuotaCookie(state: QuotaCookie): string {
  return Buffer.from(JSON.stringify(state), "utf8").toString("base64url");
}

export function isProApiKey(request: NextRequest): boolean {
  const header = request.headers.get("x-logos-api-key")?.trim();
  if (!header) return false;
  const allow = (process.env.LOGOS_RESEARCH_PRO_API_KEYS || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return allow.includes(header);
}

export function readQuotaState(request: NextRequest): QuotaCookie {
  return parseQuotaCookie(request.cookies.get(LOGOS_QUOTA_COOKIE)?.value);
}

export function applyQuotaCookie(response: NextResponse, state: QuotaCookie) {
  response.cookies.set({
    name: LOGOS_QUOTA_COOKIE,
    value: encodeQuotaCookie(state),
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24,
  });
}

export function checkAndConsumeQuota(
  request: NextRequest,
): { ok: true; state: QuotaCookie; pro: boolean } | { ok: false; state: QuotaCookie; remaining: number } {
  if (isLogosStudioQuotaDisabled() || isProApiKey(request)) {
    return { ok: true, state: readQuotaState(request), pro: true };
  }
  const state = readQuotaState(request);
  if (state.n >= LOGOS_FREE_DAILY_QUOTA) {
    return { ok: false, state, remaining: 0 };
  }
  return { ok: true, state: { d: state.d, n: state.n + 1 }, pro: false };
}

export function quotaRemaining(state: QuotaCookie, pro: boolean): number {
  if (pro || isLogosStudioQuotaDisabled()) return LOGOS_FREE_DAILY_QUOTA;
  return Math.max(0, LOGOS_FREE_DAILY_QUOTA - state.n);
}
