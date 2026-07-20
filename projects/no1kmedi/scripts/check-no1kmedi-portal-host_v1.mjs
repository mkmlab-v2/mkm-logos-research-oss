/**
 * Smoke: no1kmedi portal host rules (inline mirror of src/lib/no1kmedi-portal-host.ts).
 * Run: node ./scripts/check-no1kmedi-portal-host_v1.mjs
 */
import assert from "node:assert/strict";

const CLINIC = new Set(["clinic.no1kmedi.com", "www.clinic.no1kmedi.com"]);
const APEX = new Set(["no1kmedi.com", "www.no1kmedi.com"]);
const LOCAL = new Set(["localhost", "127.0.0.1"]);
const JEMA_AI_HUB = new Set([
  "jema-ai.com",
  "www.jema-ai.com",
  "app.jema-ai.com",
  "www.app.jema-ai.com",
]);
const JEMA_AI_NATIONAL_KM_ASK = new Set(["jema-ai.com", "www.jema-ai.com"]);
const JEMA_AI_PUBLIC_ORIGIN = "https://jema-ai.com";

function normalizeRequestHost(hostHeader) {
  return (hostHeader ?? "").split(":")[0]?.toLowerCase() ?? "";
}

function isTruthyEnv(value) {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

function devSimulateNo1kmediApex() {
  if (isTruthyEnv(process.env.MKM_DEV_SIMULATE_NO1KMEDI_APEX)) return true;
  return isTruthyEnv(process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST);
}

function devSimulateNo1kmediClinic() {
  return isTruthyEnv(process.env.MKM_DEV_SIMULATE_NO1KMEDI_CLINIC);
}

function isNo1kmediApexHost(host) {
  const h = normalizeRequestHost(host);
  if (APEX.has(h)) return true;
  return LOCAL.has(h) && devSimulateNo1kmediApex();
}

function isClinicNo1kmediHost(host) {
  const h = normalizeRequestHost(host);
  if (CLINIC.has(h)) return true;
  return LOCAL.has(h) && devSimulateNo1kmediClinic();
}

function shouldRewriteRootToNationalKmAsk(host) {
  return isNo1kmediApexHost(host);
}

function shouldRewriteRootToClinician(host) {
  return isClinicNo1kmediHost(host);
}

function shouldRedirectRootToHubHome(host, pathname, legacyHomeParam) {
  if (pathname !== "/") return false;
  if (legacyHomeParam === "1") return false;
  const h = normalizeRequestHost(host);
  if (shouldRewriteRootToNationalKmAsk(h)) return false;
  if (shouldRewriteRootToClinician(h)) return false;
  if (JEMA_AI_HUB.has(h)) return true;
  return LOCAL.has(h);
}

function isPublicPatientSurfacePath(pathname) {
  if (!pathname || pathname === "/") return false;
  return ["/intake", "/consumer"].some((base) => pathname === base || pathname.startsWith(`${base}/`));
}

function isNationalKmAskPath(pathname) {
  return pathname === "/ask" || pathname.startsWith("/ask/");
}

function isJemaAiNationalKmAskHost(host) {
  return JEMA_AI_NATIONAL_KM_ASK.has(normalizeRequestHost(host));
}

function shouldRedirectApexNationalKmAskToJemaAi(host, pathname) {
  if (!isNo1kmediApexHost(host)) return false;
  return pathname === "/" || isNationalKmAskPath(pathname);
}

function nationalKmAskCanonicalRedirectUrl(pathname, search = "") {
  const path = pathname === "/" ? "/ask" : pathname;
  return `${JEMA_AI_PUBLIC_ORIGIN}${path}${search || ""}`;
}

assert.equal(isPublicPatientSurfacePath("/intake"), true);
assert.equal(isPublicPatientSurfacePath("/consumer"), true);
assert.equal(isNationalKmAskPath("/ask"), true);
assert.equal(isNationalKmAskPath("/ask/foo"), true);

assert.equal(normalizeRequestHost("NO1KMEDI.COM:3010"), "no1kmedi.com");
assert.equal(isNo1kmediApexHost("no1kmedi.com"), true);
assert.equal(isClinicNo1kmediHost("clinic.no1kmedi.com"), true);
assert.equal(isClinicNo1kmediHost("no1kmedi.com"), false);

assert.equal(shouldRedirectRootToHubHome("app.jema-ai.com", "/", null), true);
assert.equal(shouldRedirectRootToHubHome("no1kmedi.com", "/", null), false);
assert.equal(shouldRedirectRootToHubHome("clinic.no1kmedi.com", "/", null), false);
assert.equal(shouldRewriteRootToNationalKmAsk("no1kmedi.com"), true);
assert.equal(shouldRewriteRootToClinician("no1kmedi.com"), false);
assert.equal(shouldRewriteRootToClinician("clinic.no1kmedi.com"), true);
assert.equal(shouldRewriteRootToNationalKmAsk("clinic.no1kmedi.com"), false);

assert.equal(isJemaAiNationalKmAskHost("jema-ai.com"), true);
assert.equal(isJemaAiNationalKmAskHost("www.jema-ai.com"), true);
assert.equal(isJemaAiNationalKmAskHost("app.jema-ai.com"), false);
assert.equal(shouldRedirectApexNationalKmAskToJemaAi("no1kmedi.com", "/"), true);
assert.equal(shouldRedirectApexNationalKmAskToJemaAi("no1kmedi.com", "/ask"), true);
assert.equal(shouldRedirectApexNationalKmAskToJemaAi("no1kmedi.com", "/intake"), false);
assert.equal(shouldRedirectApexNationalKmAskToJemaAi("clinic.no1kmedi.com", "/ask"), false);
assert.equal(
  nationalKmAskCanonicalRedirectUrl("/"),
  "https://jema-ai.com/ask",
);
assert.equal(
  nationalKmAskCanonicalRedirectUrl("/ask", "?q=1"),
  "https://jema-ai.com/ask?q=1",
);

const prevApex = process.env.MKM_DEV_SIMULATE_NO1KMEDI_APEX;
const prevClinic = process.env.MKM_DEV_SIMULATE_NO1KMEDI_CLINIC;
const prevHost = process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST;

process.env.MKM_DEV_SIMULATE_NO1KMEDI_APEX = "1";
process.env.MKM_DEV_SIMULATE_NO1KMEDI_CLINIC = "";
process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST = "";
assert.equal(shouldRewriteRootToNationalKmAsk("localhost"), true);
assert.equal(shouldRewriteRootToClinician("localhost"), false);
assert.equal(shouldRedirectApexNationalKmAskToJemaAi("localhost", "/ask"), true);

process.env.MKM_DEV_SIMULATE_NO1KMEDI_APEX = "";
process.env.MKM_DEV_SIMULATE_NO1KMEDI_CLINIC = "1";
assert.equal(shouldRewriteRootToClinician("localhost"), true);
assert.equal(shouldRewriteRootToNationalKmAsk("localhost"), false);

process.env.MKM_DEV_SIMULATE_NO1KMEDI_APEX = prevApex ?? "";
process.env.MKM_DEV_SIMULATE_NO1KMEDI_CLINIC = prevClinic ?? "";
process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST = prevHost ?? "";

console.log("check-no1kmedi-portal-host_v1: ok");
