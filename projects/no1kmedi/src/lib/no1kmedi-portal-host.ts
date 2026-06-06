/** no1kmedi.com / clinic.no1kmedi.com — clinician portal host detection (middleware + UI). */

export const JEMA_AI_PUBLIC_ORIGIN = "https://jema-ai.com";

export const CLINIC_NO1KMEDI_HOSTS = new Set([
  "clinic.no1kmedi.com",
  "www.clinic.no1kmedi.com",
]);

export const NO1KMEDI_APEX_PORTAL_HOSTS = new Set([
  "no1kmedi.com",
  "www.no1kmedi.com",
]);

export const LOCAL_DEV_HOSTS = new Set(["localhost", "127.0.0.1"]);

/** Official clinician app host — minimal ChatGPT shell on /clinician (not apex hub rewrite). */
export const JEMA_APP_CLINICIAN_MINIMAL_HOSTS = new Set([
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

/** Local dev: treat localhost like no1kmedi apex when MKM_DEV_SIMULATE_NO1KMEDI_HOST is truthy. */
export function devSimulateNo1kmediPortal(): boolean {
  return isTruthyEnv(process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST);
}

export function isNo1kmediPortalHost(host: string): boolean {
  const h = normalizeRequestHost(host);
  return CLINIC_NO1KMEDI_HOSTS.has(h) || NO1KMEDI_APEX_PORTAL_HOSTS.has(h);
}

export function shouldRewriteRootToClinician(host: string): boolean {
  const h = normalizeRequestHost(host);
  if (isNo1kmediPortalHost(h)) return true;
  return LOCAL_DEV_HOSTS.has(h) && devSimulateNo1kmediPortal();
}

/** ChatGPT-minimal shell on no1kmedi hosts, app.jema-ai.com /clinician, and localhost when dev simulate is on. */
export function shouldUseMinimalClinicianShell(host: string): boolean {
  const h = normalizeRequestHost(host);
  if (JEMA_APP_CLINICIAN_MINIMAL_HOSTS.has(h)) return true;
  return shouldRewriteRootToClinician(h);
}
