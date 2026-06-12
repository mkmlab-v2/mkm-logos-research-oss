import { NextRequest, NextResponse } from "next/server";

import { buildGoogleAuthUrl } from "@/lib/mkmFamilyGoogleOAuthV1";
import {
  clearOAuthStateCookie,
  isSecureRequest,
  newOAuthState,
  requireMkmFamilyAuthConfigured,
  setOAuthStateCookie,
} from "@/lib/mkmFamilyHttpV1";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const blocked = requireMkmFamilyAuthConfigured();
  if (blocked) return blocked;

  const returnTo = request.nextUrl.searchParams.get("return_to") || "/hub";
  const safeReturn = returnTo.startsWith("/") && !returnTo.startsWith("//") ? returnTo : "/hub";

  try {
    const state = `${newOAuthState()}:${Buffer.from(safeReturn, "utf8").toString("base64url")}`;
    const url = buildGoogleAuthUrl(state);
    const res = NextResponse.redirect(url);
    setOAuthStateCookie(res, state, isSecureRequest(request));
    return res;
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "google_auth_start_failed" },
      { status: 500 },
    );
  }
}
