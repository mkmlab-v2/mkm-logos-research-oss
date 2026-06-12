import { createHmac, timingSafeEqual } from "crypto";

import { MKM_FAMILY_SESSION_MAX_AGE_SEC } from "@/lib/mkmFamilyAuthConfigV1";

export type MkmFamilySessionPayload = {
  sub: string;
  email: string;
  iat: number;
  exp: number;
};

function b64url(input: Buffer | string): string {
  const buf = typeof input === "string" ? Buffer.from(input, "utf8") : input;
  return buf.toString("base64url");
}

function fromB64url(input: string): Buffer {
  return Buffer.from(input, "base64url");
}

export function signMkmFamilySession(
  payload: Omit<MkmFamilySessionPayload, "iat" | "exp">,
  secret: string,
  nowSec = Math.floor(Date.now() / 1000),
): string {
  const full: MkmFamilySessionPayload = {
    ...payload,
    iat: nowSec,
    exp: nowSec + MKM_FAMILY_SESSION_MAX_AGE_SEC,
  };
  const header = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = b64url(JSON.stringify(full));
  const sig = createHmac("sha256", secret).update(`${header}.${body}`).digest("base64url");
  return `${header}.${body}.${sig}`;
}

export function verifyMkmFamilySession(
  token: string,
  secret: string,
  nowSec = Math.floor(Date.now() / 1000),
): MkmFamilySessionPayload | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [header, body, sig] = parts;
  const expected = createHmac("sha256", secret).update(`${header}.${body}`).digest("base64url");
  try {
    const a = Buffer.from(sig, "utf8");
    const b = Buffer.from(expected, "utf8");
    if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  } catch {
    return null;
  }
  try {
    const payload = JSON.parse(fromB64url(body).toString("utf8")) as MkmFamilySessionPayload;
    if (!payload.sub || !payload.email || !payload.exp) return null;
    if (payload.exp < nowSec) return null;
    return payload;
  } catch {
    return null;
  }
}

export function newMkmAccountId(): string {
  const hex = crypto.randomUUID().replace(/-/g, "").slice(0, 16);
  return `mkm_acc_${hex}`;
}
