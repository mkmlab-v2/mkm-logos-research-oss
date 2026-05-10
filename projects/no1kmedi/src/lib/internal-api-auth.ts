/**
 * Internal/admin API contract: server env NO1KMEDI_ADMIN_TOKEN must match either
 * header x-no1kmedi-admin-token or Authorization: Bearer <token>.
 * When the env var is unset, access is allowed (local/dev parity with existing routes).
 */
import { timingSafeEqual } from "crypto";
import type { NextRequest } from "next/server";

export const NO1KMEDI_ADMIN_HEADER = "x-no1kmedi-admin-token";

export function getConfiguredAdminToken(): string | undefined {
  const t = process.env.NO1KMEDI_ADMIN_TOKEN?.trim();
  return t || undefined;
}

function timingSafeEqualStrings(expected: string, provided: string): boolean {
  try {
    const a = Buffer.from(expected, "utf8");
    const b = Buffer.from(provided, "utf8");
    if (a.length !== b.length) return false;
    return timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

/** Token from custom header or Bearer (does not read JSON body). */
export function extractRequestAdminToken(request: NextRequest): string {
  const headerToken = request.headers.get(NO1KMEDI_ADMIN_HEADER)?.trim();
  if (headerToken) return headerToken;
  const bearer = request.headers.get("authorization");
  if (bearer?.startsWith("Bearer ")) {
    return bearer.slice("Bearer ".length).trim();
  }
  return "";
}

export function isAdminTokenValid(provided: string): boolean {
  const configured = getConfiguredAdminToken();
  if (!configured) return true;
  if (!provided.trim()) return false;
  return timingSafeEqualStrings(configured, provided.trim());
}

export function hasAdminTokenAccess(request: NextRequest): boolean {
  return isAdminTokenValid(extractRequestAdminToken(request));
}

/** Use when the route also accepts a token from JSON (legacy body fields). */
export function hasAdminTokenAccessWithOptionalBodyToken(
  request: NextRequest,
  bodyToken?: string | null,
): boolean {
  const fromRequest = extractRequestAdminToken(request);
  const provided = (fromRequest || String(bodyToken || "").trim()).trim();
  return isAdminTokenValid(provided);
}
