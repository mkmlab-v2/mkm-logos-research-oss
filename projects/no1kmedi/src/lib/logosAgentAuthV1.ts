import { randomBytes } from "node:crypto";

import { LOGOS_CANONICAL_ORIGIN } from "@/lib/logosAgentAuthDiscoveryV1";
import { signLogosAgentAccessToken } from "@/lib/logosAgentAuthJwtV1";
import {
  countRecentRegistrationsForEmail,
  getRegistrationByClaimAttemptToken,
  getRegistrationByClaimToken,
  putRegistration,
} from "@/lib/logosAgentAuthStoreV1";
import type {
  LogosAgentRegistrationRecord,
  LogosAgentScope,
} from "@/lib/logosAgentAuthTypesV1";
import { LOGOS_AGENT_SCOPES } from "@/lib/logosAgentAuthTypesV1";

export const LOGOS_CLAIM_USER_CODE_TTL_SEC = 600;
export const LOGOS_CLAIM_TOKEN_TTL_SEC = 3600;
export const LOGOS_CLAIM_POLL_INTERVAL_SEC = 5;

function nowIso(): string {
  return new Date().toISOString();
}

function addSecIso(sec: number): string {
  return new Date(Date.now() + sec * 1000).toISOString();
}

function isExpired(iso: string): boolean {
  return Date.parse(iso) <= Date.now();
}

function newId(prefix: string): string {
  return `${prefix}_${randomBytes(10).toString("hex")}`;
}

function newUserCode(): string {
  return String(Math.floor(100000 + Math.random() * 900000));
}

export function isValidEmail(value: string): boolean {
  const v = value.trim();
  return v.includes("@") && v.includes(".") && v.length <= 254;
}

/** Empty env = open; comma-separated domains e.g. `seminary.edu,publisher.co.kr` */
export function isEmailDomainAllowed(email: string): boolean {
  const allowlist = process.env.LOGOS_AGENT_AUTH_EMAIL_DOMAIN_ALLOWLIST?.trim();
  if (!allowlist) return true;
  const domain = email.trim().toLowerCase().split("@")[1];
  if (!domain) return false;
  const allowed = allowlist
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  return allowed.includes(domain);
}

export function defaultPostClaimScopes(): LogosAgentScope[] {
  const fromEnv = process.env.LOGOS_AGENT_AUTH_DEFAULT_SCOPES?.trim();
  if (fromEnv) {
    const allowed = new Set(LOGOS_AGENT_SCOPES);
    const picked = fromEnv
      .split(",")
      .map((s) => s.trim())
      .filter((s): s is LogosAgentScope => allowed.has(s as LogosAgentScope));
    if (picked.length) return picked;
  }
  return ["logos.presets.read", "logos.query.read", "logos.evidence.write"];
}

export function claimVerificationUri(claimAttemptToken: string, origin?: string): string {
  const base = (origin || LOGOS_CANONICAL_ORIGIN).replace(/\/$/, "");
  const q = new URLSearchParams({ claim_attempt_token: claimAttemptToken });
  return `${base}/logos-research/agent-claim?${q.toString()}`;
}

export function claimBlock(row: LogosAgentRegistrationRecord, origin?: string) {
  return {
    user_code: row.user_code,
    expires_in: Math.max(
      0,
      Math.floor((Date.parse(row.user_code_expires) - Date.now()) / 1000),
    ),
    verification_uri: claimVerificationUri(row.claim_attempt_token, origin),
    interval: LOGOS_CLAIM_POLL_INTERVAL_SEC,
  };
}

export async function registerServiceAuth(input: {
  login_hint: string;
  origin?: string;
}): Promise<
  | { ok: true; body: Record<string, unknown> }
  | { ok: false; status: number; body: Record<string, unknown> }
> {
  const email = input.login_hint.trim().toLowerCase();
  if (!isValidEmail(email)) {
    return { ok: false, status: 400, body: { error: "invalid_login_hint" } };
  }
  if (!isEmailDomainAllowed(email)) {
    return {
      ok: false,
      status: 403,
      body: {
        error: "email_domain_not_allowed",
        hint: "Institution pilot — contact lead form or operator allowlist.",
      },
    };
  }

  const recent = await countRecentRegistrationsForEmail(email, 60 * 60 * 1000);
  if (recent >= 8) {
    return { ok: false, status: 429, body: { error: "rate_limited", retry_after_sec: 3600 } };
  }

  const registration_id = newId("reg");
  const claim_token = newId("clm");
  const claim_attempt_token = newId("cat");
  const user_code = newUserCode();
  const post_claim_scopes = defaultPostClaimScopes();

  const row: LogosAgentRegistrationRecord = {
    registration_id,
    registration_type: "service_auth",
    login_hint: email,
    claim_token,
    claim_token_expires: addSecIso(LOGOS_CLAIM_TOKEN_TTL_SEC),
    user_code,
    user_code_expires: addSecIso(LOGOS_CLAIM_USER_CODE_TTL_SEC),
    claim_attempt_token,
    post_claim_scopes,
    claimed: false,
    created_at: nowIso(),
  };
  await putRegistration(row);

  return {
    ok: true,
    body: {
      registration_id,
      registration_type: "service_auth",
      claim_url: `${LOGOS_CANONICAL_ORIGIN}/api/agent/identity/claim`,
      claim_token,
      claim_token_expires: row.claim_token_expires,
      post_claim_scopes,
      claim: claimBlock(row, input.origin),
      research_only: true,
      send_gate: "HOLD",
    },
  };
}

export async function refreshClaimAttempt(input: {
  claim_token: string;
  email?: string;
  origin?: string;
}): Promise<
  | { ok: true; body: Record<string, unknown> }
  | { ok: false; status: number; body: Record<string, unknown> }
> {
  const row = await getRegistrationByClaimToken(input.claim_token);
  if (!row) return { ok: false, status: 400, body: { error: "invalid_claim_token" } };
  if (isExpired(row.claim_token_expires)) {
    return { ok: false, status: 400, body: { error: "expired_token" } };
  }
  if (row.claimed) {
    return { ok: false, status: 400, body: { error: "already_claimed" } };
  }
  if (input.email && input.email.trim().toLowerCase() !== row.login_hint) {
    return { ok: false, status: 400, body: { error: "email_mismatch" } };
  }

  const next: LogosAgentRegistrationRecord = {
    ...row,
    user_code: newUserCode(),
    user_code_expires: addSecIso(LOGOS_CLAIM_USER_CODE_TTL_SEC),
    claim_attempt_token: newId("cat"),
  };
  await putRegistration(next);

  return {
    ok: true,
    body: {
      claim_attempt_token: next.claim_attempt_token,
      claim: claimBlock(next, input.origin),
    },
  };
}

export async function completeClaim(input: {
  claim_attempt_token: string;
  user_code: string;
  email?: string;
}): Promise<
  | { ok: true; body: Record<string, unknown> }
  | { ok: false; status: number; body: Record<string, unknown> }
> {
  const row = await getRegistrationByClaimAttemptToken(input.claim_attempt_token);
  if (!row) return { ok: false, status: 400, body: { error: "invalid_claim_attempt" } };
  if (isExpired(row.claim_token_expires)) {
    return { ok: false, status: 400, body: { error: "expired_token" } };
  }
  if (isExpired(row.user_code_expires)) {
    return { ok: false, status: 400, body: { error: "expired_user_code" } };
  }
  if (row.claimed) {
    return { ok: true, body: { ok: true, already_claimed: true, registration_id: row.registration_id } };
  }

  const code = input.user_code.trim();
  if (code !== row.user_code) {
    return { ok: false, status: 400, body: { error: "invalid_user_code" } };
  }
  if (input.email && input.email.trim().toLowerCase() !== row.login_hint) {
    return { ok: false, status: 400, body: { error: "email_mismatch" } };
  }

  const claimed: LogosAgentRegistrationRecord = {
    ...row,
    claimed: true,
    claimed_at: nowIso(),
  };
  await putRegistration(claimed);

  return {
    ok: true,
    body: {
      ok: true,
      registration_id: claimed.registration_id,
      email: claimed.login_hint,
      scopes: claimed.post_claim_scopes,
    },
  };
}

export async function exchangeClaimToken(claimToken: string): Promise<
  | { ok: true; body: Record<string, unknown> }
  | { ok: false; status: number; body: Record<string, unknown> }
> {
  const row = await getRegistrationByClaimToken(claimToken);
  if (!row) return { ok: false, status: 400, body: { error: "invalid_claim_token" } };
  if (isExpired(row.claim_token_expires)) {
    return { ok: false, status: 400, body: { error: "expired_token" } };
  }
  if (!row.claimed) {
    return {
      ok: false,
      status: 400,
      body: { error: "authorization_pending", error_description: "User claim not completed" },
    };
  }

  const token = signLogosAgentAccessToken({
    sub: row.registration_id,
    email: row.login_hint,
    scopes: row.post_claim_scopes,
  });

  return {
    ok: true,
    body: {
      access_token: token.access_token,
      token_type: "Bearer",
      expires_in: token.expires_in,
      scope: row.post_claim_scopes.join(" "),
      registration_id: row.registration_id,
      research_only: true,
    },
  };
}

export function requestOrigin(headers: Headers): string | undefined {
  const host = headers.get("x-forwarded-host") || headers.get("host");
  if (!host) return undefined;
  const proto = headers.get("x-forwarded-proto") || "https";
  return `${proto}://${host}`;
}
