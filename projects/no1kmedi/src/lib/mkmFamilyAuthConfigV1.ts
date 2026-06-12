/** MKM Family identity — jema-ai.com IdP anchor (federation, not product DB merge). */

export const MKM_FAMILY_SESSION_COOKIE = "mkm_family_session";
export const MKM_FAMILY_OAUTH_STATE_COOKIE = "mkm_family_oauth_state";
export const MKM_FAMILY_SESSION_MAX_AGE_SEC = 60 * 60 * 24 * 30;

export type MkmFamilyRpProduct = "mkmlife" | "personadiary";

export function mkmFamilyPublicOrigin(): string {
  const raw =
    process.env.MKM_FAMILY_PUBLIC_ORIGIN?.trim() ||
    process.env.NEXT_PUBLIC_SITE_URL?.trim() ||
    "https://app.jema-ai.com";
  return raw.replace(/\/$/, "");
}

export function mkmFamilyAuthSecret(): string | null {
  const v = process.env.MKM_FAMILY_AUTH_SECRET?.trim();
  return v || null;
}

export function googleOAuthClientId(): string | null {
  return process.env.GOOGLE_OAUTH_CLIENT_ID?.trim() || null;
}

export function googleOAuthClientSecret(): string | null {
  return process.env.GOOGLE_OAUTH_CLIENT_SECRET?.trim() || null;
}

export function mkmFamilyGoogleAuthEnabled(): boolean {
  return !!(mkmFamilyAuthSecret() && googleOAuthClientId() && googleOAuthClientSecret());
}

export function mkmFamilyRpOrigin(product: MkmFamilyRpProduct): string {
  if (product === "mkmlife") {
    return (process.env.MKM_FAMILY_RP_MKMLIFE_ORIGIN || "https://mkmlife.com").replace(/\/$/, "");
  }
  return (process.env.MKM_FAMILY_RP_PERSONADIARY_ORIGIN || "https://personadiary.com").replace(/\/$/, "");
}

export const MKM_FAMILY_RP_CORS_ORIGINS = [
  "https://mkmlife.com",
  "https://www.mkmlife.com",
  "https://personadiary.com",
  "https://www.personadiary.com",
  "https://app.jema-ai.com",
  "https://jema-ai.com",
  "http://localhost:3010",
  "http://localhost:3000",
];
