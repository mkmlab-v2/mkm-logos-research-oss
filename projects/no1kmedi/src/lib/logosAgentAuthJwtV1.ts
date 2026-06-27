import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

import { LOGOS_CANONICAL_ORIGIN } from "@/lib/logosAgentAuthDiscoveryV1";
import type { LogosAgentScope } from "@/lib/logosAgentAuthTypesV1";

const DEFAULT_TTL_SEC = 60 * 60;

function b64url(input: Buffer | string): string {
  const buf = typeof input === "string" ? Buffer.from(input, "utf8") : input;
  return buf.toString("base64url");
}

function parseB64urlJson<T>(segment: string): T | null {
  try {
    return JSON.parse(Buffer.from(segment, "base64url").toString("utf8")) as T;
  } catch {
    return null;
  }
}

export function logosAgentAuthJwtSecret(): string {
  const fromEnv = process.env.LOGOS_AGENT_AUTH_JWT_SECRET?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.NODE_ENV === "production") {
    throw new Error("LOGOS_AGENT_AUTH_JWT_SECRET_required_in_production");
  }
  return "logos-agent-auth-dev-only-secret";
}

export function newJti(): string {
  return `jti_${randomBytes(12).toString("hex")}`;
}

export function signLogosAgentAccessToken(input: {
  sub: string;
  email: string;
  scopes: LogosAgentScope[];
  ttlSec?: number;
}): { access_token: string; expires_in: number; jti: string } {
  const ttl = input.ttlSec ?? DEFAULT_TTL_SEC;
  const now = Math.floor(Date.now() / 1000);
  const jti = newJti();
  const header = { alg: "HS256", typ: "JWT" };
  const payload = {
    iss: LOGOS_CANONICAL_ORIGIN,
    aud: `${LOGOS_CANONICAL_ORIGIN}/`,
    sub: input.sub,
    email: input.email,
    scope: input.scopes.join(" "),
    jti,
    iat: now,
    exp: now + ttl,
  };
  const head = b64url(JSON.stringify(header));
  const body = b64url(JSON.stringify(payload));
  const sig = createHmac("sha256", logosAgentAuthJwtSecret())
    .update(`${head}.${body}`)
    .digest("base64url");
  return { access_token: `${head}.${body}.${sig}`, expires_in: ttl, jti };
}

export function verifyLogosAgentAccessToken(token: string): {
  sub: string;
  email: string;
  scopes: LogosAgentScope[];
  jti: string;
  exp: number;
} | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [head, body, sig] = parts;
  const expected = createHmac("sha256", logosAgentAuthJwtSecret())
    .update(`${head}.${body}`)
    .digest("base64url");
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;

  const payload = parseB64urlJson<{
    iss?: string;
    aud?: string;
    sub?: string;
    email?: string;
    scope?: string;
    jti?: string;
    exp?: number;
  }>(body);
  if (!payload?.sub || !payload.email || !payload.jti || !payload.exp) return null;
  if (payload.iss !== LOGOS_CANONICAL_ORIGIN) return null;
  if (payload.aud !== `${LOGOS_CANONICAL_ORIGIN}/`) return null;
  if (payload.exp <= Math.floor(Date.now() / 1000)) return null;

  const scopes = (payload.scope || "")
    .split(/\s+/)
    .map((s) => s.trim())
    .filter(Boolean) as LogosAgentScope[];

  return {
    sub: payload.sub,
    email: payload.email,
    scopes,
    jti: payload.jti,
    exp: payload.exp,
  };
}
