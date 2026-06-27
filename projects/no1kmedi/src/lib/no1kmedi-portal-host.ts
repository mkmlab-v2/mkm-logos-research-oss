/** no1kmedi.com (대국민 한의학 AI) / clinic.no1kmedi.com (한의사 모드) — host detection. */

export const JEMA_AI_PUBLIC_ORIGIN = "https://jema-ai.com";

export const CLINIC_NO1KMEDI_ORIGIN = "https://clinic.no1kmedi.com";

export const CLINIC_NO1KMEDI_HOSTS = new Set([
  "clinic.no1kmedi.com",
  "www.clinic.no1kmedi.com",
]);

/** 대국민 한의학 Q&A — apex only (not clinician portal). */
export const NO1KMEDI_APEX_PORTAL_HOSTS = new Set([
  "no1kmedi.com",
  "www.no1kmedi.com",
]);

export const LOCAL_DEV_HOSTS = new Set(["localhost", "127.0.0.1"]);

/** Official clinician app host — minimal chat shell on /clinician (not apex hub rewrite). */
export const JEMA_APP_CLINICIAN_MINIMAL_HOSTS = new Set([
  "app.jema-ai.com",
  "www.app.jema-ai.com",
]);

/** jema-ai.com brand hosts — HQ `/hub` facade entry (not no1kmedi clinician portal). */
export const JEMA_AI_HUB_HOSTS = new Set([
  "jema-ai.com",
  "www.jema-ai.com",
  "app.jema-ai.com",
  "www.app.jema-ai.com",
]);

export function normalizeRequestHost(hostHeader: string | null | undefined): string {
  return (hostHeader ?? "").split(":")[0]?.toLowerCase() ?? "";
}

export function isTruthyEnv(value: string | undefined): boolean {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

/** Local dev: localhost as no1kmedi.com apex → /ask (national KM). */
export function devSimulateNo1kmediApex(): boolean {
  if (isTruthyEnv(process.env.MKM_DEV_SIMULATE_NO1KMEDI_APEX)) return true;
  return isTruthyEnv(process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST);
}

/** Local dev: localhost as clinic.no1kmedi.com → /clinician. */
export function devSimulateNo1kmediClinic(): boolean {
  return isTruthyEnv(process.env.MKM_DEV_SIMULATE_NO1KMEDI_CLINIC);
}

export function isNo1kmediApexHost(host: string): boolean {
  const h = normalizeRequestHost(host);
  if (NO1KMEDI_APEX_PORTAL_HOSTS.has(h)) return true;
  return LOCAL_DEV_HOSTS.has(h) && devSimulateNo1kmediApex();
}

export function isClinicNo1kmediHost(host: string): boolean {
  const h = normalizeRequestHost(host);
  if (CLINIC_NO1KMEDI_HOSTS.has(h)) return true;
  return LOCAL_DEV_HOSTS.has(h) && devSimulateNo1kmediClinic();
}

/** @deprecated Use isNo1kmediApexHost / isClinicNo1kmediHost */
export function isNo1kmediPortalHost(host: string): boolean {
  return isNo1kmediApexHost(host) || isClinicNo1kmediHost(host);
}

export function shouldRewriteRootToNationalKmAsk(host: string): boolean {
  return isNo1kmediApexHost(host);
}

export function shouldRewriteRootToClinician(host: string): boolean {
  return isClinicNo1kmediHost(host);
}

/** Patient-facing hub routes — must not be prefixed with /clinician on portal hosts. */
export function isPublicPatientSurfacePath(pathname: string): boolean {
  if (!pathname || pathname === "/") return false;
  const paths = ["/intake", "/consumer"];
  return paths.some((base) => pathname === base || pathname.startsWith(`${base}/`));
}

/** Minimal clinician shell: clinic.*, app.jema-ai.com /clinician, localhost clinic simulate. */
export function shouldUseMinimalClinicianShell(host: string): boolean {
  const h = normalizeRequestHost(host);
  if (JEMA_APP_CLINICIAN_MINIMAL_HOSTS.has(h)) return true;
  return isClinicNo1kmediHost(h);
}

/** Paste Chart v1 bookmark — Antigravity scope applies only on this panel. */
export const CLINICIAN_PASTE_CHART_PANEL = "gold" as const;

/** Clinic portal / minimal shell: land on Paste Chart, not legacy 진료 분석. */
export function defaultClinicianPanelForHost(host: string): "gold" | "copilot" {
  return shouldUseMinimalClinicianShell(host) ? CLINICIAN_PASTE_CHART_PANEL : "copilot";
}

/** National KM ask surface paths on apex (must not redirect to /clinician). */
export function isNationalKmAskPath(pathname: string): boolean {
  return pathname === "/ask" || pathname.startsWith("/ask/");
}

/** Redirect `/` → `/hub` on JEMA HQ hosts (and local dev unless simulating no1kmedi hosts). */
export function shouldRedirectRootToHubHome(
  host: string,
  pathname: string,
  legacyHomeParam: string | null | undefined,
): boolean {
  if (pathname !== "/") return false;
  if (legacyHomeParam === "1") return false;
  const h = normalizeRequestHost(host);
  if (shouldRewriteRootToNationalKmAsk(h)) return false;
  if (shouldRewriteRootToClinician(h)) return false;
  if (JEMA_AI_HUB_HOSTS.has(h)) return true;
  return LOCAL_DEV_HOSTS.has(h);
}
