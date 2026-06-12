import { cookies } from "next/headers";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import {
  MKM_FAMILY_OAUTH_STATE_COOKIE,
  MKM_FAMILY_RP_CORS_ORIGINS,
  MKM_FAMILY_SESSION_COOKIE,
  MKM_FAMILY_SESSION_MAX_AGE_SEC,
  mkmFamilyAuthSecret,
  mkmFamilyGoogleAuthEnabled,
  mkmFamilyPublicOrigin,
} from "@/lib/mkmFamilyAuthConfigV1";
import { verifyMkmFamilySession, type MkmFamilySessionPayload } from "@/lib/mkmFamilySessionV1";

export function mkmFamilyAuthDisabledResponse(): NextResponse {
  return NextResponse.json(
    {
      ok: false,
      error: "mkm_family_auth_not_configured",
      hint: "Set MKM_FAMILY_AUTH_SECRET, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET",
    },
    { status: 503 },
  );
}

export function requireMkmFamilyAuthConfigured(): NextResponse | null {
  if (!mkmFamilyGoogleAuthEnabled()) return mkmFamilyAuthDisabledResponse();
  return null;
}

export function sessionCookieOptions(secure: boolean) {
  return {
    httpOnly: true,
    secure,
    sameSite: "lax" as const,
    path: "/",
    maxAge: MKM_FAMILY_SESSION_MAX_AGE_SEC,
  };
}

export function setSessionCookie(res: NextResponse, token: string, secure: boolean): void {
  res.cookies.set(MKM_FAMILY_SESSION_COOKIE, token, sessionCookieOptions(secure));
}

export function clearSessionCookie(res: NextResponse): void {
  res.cookies.set(MKM_FAMILY_SESSION_COOKIE, "", { ...sessionCookieOptions(true), maxAge: 0 });
}

export function readSessionFromRequest(request: NextRequest): MkmFamilySessionPayload | null {
  const secret = mkmFamilyAuthSecret();
  if (!secret) return null;
  const token = request.cookies.get(MKM_FAMILY_SESSION_COOKIE)?.value;
  if (!token) return null;
  return verifyMkmFamilySession(token, secret);
}

export async function readSessionFromCookies(): Promise<MkmFamilySessionPayload | null> {
  const secret = mkmFamilyAuthSecret();
  if (!secret) return null;
  const token = cookies().get(MKM_FAMILY_SESSION_COOKIE)?.value;
  if (!token) return null;
  return verifyMkmFamilySession(token, secret);
}

export function isSecureRequest(request: NextRequest): boolean {
  const proto = request.headers.get("x-forwarded-proto");
  if (proto) return proto === "https";
  return mkmFamilyPublicOrigin().startsWith("https://");
}

export function corsPreflightResponse(origin: string | null): NextResponse | null {
  if (!origin || !MKM_FAMILY_RP_CORS_ORIGINS.includes(origin)) return null;
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
    },
  });
}

export function withCorsJson(
  origin: string | null,
  body: unknown,
  init?: { status?: number },
): NextResponse {
  const res = NextResponse.json(body, { status: init?.status ?? 200 });
  if (origin && MKM_FAMILY_RP_CORS_ORIGINS.includes(origin)) {
    res.headers.set("Access-Control-Allow-Origin", origin);
    res.headers.set("Vary", "Origin");
  }
  return res;
}

export function newOAuthState(): string {
  return crypto.randomUUID();
}

export function setOAuthStateCookie(res: NextResponse, state: string, secure: boolean): void {
  res.cookies.set(MKM_FAMILY_OAUTH_STATE_COOKIE, state, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: 600,
  });
}

export function readOAuthState(request: NextRequest): string | undefined {
  return request.cookies.get(MKM_FAMILY_OAUTH_STATE_COOKIE)?.value;
}

export function clearOAuthStateCookie(res: NextResponse): void {
  res.cookies.set(MKM_FAMILY_OAUTH_STATE_COOKIE, "", { path: "/", maxAge: 0 });
}
