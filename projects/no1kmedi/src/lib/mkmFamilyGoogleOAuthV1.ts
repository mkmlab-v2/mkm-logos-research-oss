import {
  googleOAuthClientId,
  googleOAuthClientSecret,
  mkmFamilyPublicOrigin,
} from "@/lib/mkmFamilyAuthConfigV1";

const GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth";
const GOOGLE_TOKEN = "https://oauth2.googleapis.com/token";
const GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo";

export function googleOAuthCallbackUrl(): string {
  return `${mkmFamilyPublicOrigin()}/api/mkm-family/auth/google/callback`;
}

export function buildGoogleAuthUrl(state: string): string {
  const clientId = googleOAuthClientId();
  if (!clientId) throw new Error("GOOGLE_OAUTH_CLIENT_ID missing");
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: googleOAuthCallbackUrl(),
    response_type: "code",
    scope: "openid email profile",
    state,
    access_type: "online",
    prompt: "select_account",
  });
  return `${GOOGLE_AUTH}?${params.toString()}`;
}

export type GoogleUserInfo = {
  sub: string;
  email: string;
  email_verified: boolean;
  name?: string;
  picture?: string;
};

export async function exchangeGoogleCode(code: string): Promise<GoogleUserInfo> {
  const clientId = googleOAuthClientId();
  const clientSecret = googleOAuthClientSecret();
  if (!clientId || !clientSecret) throw new Error("Google OAuth client not configured");

  const tokenRes = await fetch(GOOGLE_TOKEN, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: clientId,
      client_secret: clientSecret,
      redirect_uri: googleOAuthCallbackUrl(),
      grant_type: "authorization_code",
    }),
  });

  if (!tokenRes.ok) {
    const err = await tokenRes.text();
    throw new Error(`Google token exchange failed: ${tokenRes.status} ${err.slice(0, 200)}`);
  }

  const tokenJson = (await tokenRes.json()) as { access_token?: string };
  if (!tokenJson.access_token) throw new Error("Google token missing access_token");

  const userRes = await fetch(GOOGLE_USERINFO, {
    headers: { Authorization: `Bearer ${tokenJson.access_token}` },
  });
  if (!userRes.ok) {
    throw new Error(`Google userinfo failed: ${userRes.status}`);
  }
  const user = (await userRes.json()) as GoogleUserInfo;
  if (!user.sub || !user.email) throw new Error("Google userinfo incomplete");
  return user;
}
