import { NextRequest, NextResponse } from "next/server";

import { upsertGoogleAccount } from "@/lib/mkmFamilyAccountStoreV1";
import { mkmFamilyAuthSecret, mkmFamilyPublicOrigin } from "@/lib/mkmFamilyAuthConfigV1";
import { exchangeGoogleCode } from "@/lib/mkmFamilyGoogleOAuthV1";
import {
  clearOAuthStateCookie,
  isSecureRequest,
  readOAuthState,
  requireMkmFamilyAuthConfigured,
  setSessionCookie,
} from "@/lib/mkmFamilyHttpV1";
import { signMkmFamilySession } from "@/lib/mkmFamilySessionV1";

export const runtime = "nodejs";

function parseReturnPath(stateParam: string | null, cookieState: string | undefined): string {
  const state = stateParam || cookieState || "";
  const idx = state.indexOf(":");
  if (idx < 0) return "/hub";
  try {
    const decoded = Buffer.from(state.slice(idx + 1), "base64url").toString("utf8");
    if (decoded.startsWith("/") && !decoded.startsWith("//")) return decoded;
  } catch {
    /* ignore */
  }
  return "/hub";
}

export async function GET(request: NextRequest) {
  const blocked = requireMkmFamilyAuthConfigured();
  if (blocked) return blocked;

  const err = request.nextUrl.searchParams.get("error");
  if (err) {
    return NextResponse.redirect(`${mkmFamilyPublicOrigin()}/hub?auth_error=${encodeURIComponent(err)}`);
  }

  const code = request.nextUrl.searchParams.get("code");
  const stateParam = request.nextUrl.searchParams.get("state");
  const cookieState = readOAuthState(request);
  if (!code) {
    return NextResponse.redirect(`${mkmFamilyPublicOrigin()}/hub?auth_error=missing_code`);
  }
  if (!stateParam || !cookieState || stateParam !== cookieState) {
    return NextResponse.redirect(`${mkmFamilyPublicOrigin()}/hub?auth_error=invalid_state`);
  }

  const returnPath = parseReturnPath(stateParam, cookieState);
  const secret = mkmFamilyAuthSecret();
  if (!secret) return blocked!;

  try {
    const googleUser = await exchangeGoogleCode(code);
    const account = await upsertGoogleAccount({
      email: googleUser.email,
      email_verified: !!googleUser.email_verified,
      display_name: googleUser.name,
      picture_url: googleUser.picture,
      google_sub: googleUser.sub,
    });

    const token = signMkmFamilySession(
      { sub: account.mkm_account_id, email: account.email },
      secret,
    );
    const res = NextResponse.redirect(`${mkmFamilyPublicOrigin()}${returnPath}`);
    setSessionCookie(res, token, isSecureRequest(request));
    clearOAuthStateCookie(res);
    return res;
  } catch (e) {
    const msg = e instanceof Error ? e.message : "callback_failed";
    return NextResponse.redirect(`${mkmFamilyPublicOrigin()}/hub?auth_error=${encodeURIComponent(msg.slice(0, 120))}`);
  }
}
