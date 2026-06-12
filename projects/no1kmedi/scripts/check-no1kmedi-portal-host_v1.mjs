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

function normalizeRequestHost(hostHeader) {
  return (hostHeader ?? "").split(":")[0]?.toLowerCase() ?? "";
}

function isTruthyEnv(value) {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

function isNo1kmediPortalHost(host) {
  const h = normalizeRequestHost(host);
  return CLINIC.has(h) || APEX.has(h);
}

function shouldRewriteRootToClinician(host) {
  const h = normalizeRequestHost(host);
  if (isNo1kmediPortalHost(h)) return true;
  return LOCAL.has(h) && isTruthyEnv(process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST);
}

function shouldRedirectRootToHubHome(host, pathname, legacyHomeParam) {
  if (pathname !== "/") return false;
  if (legacyHomeParam === "1") return false;
  const h = normalizeRequestHost(host);
  if (shouldRewriteRootToClinician(h)) return false;
  if (JEMA_AI_HUB.has(h)) return true;
  return LOCAL.has(h);
}

function isPublicPatientSurfacePath(pathname) {
  if (!pathname || pathname === "/") return false;
  return ["/intake", "/consumer"].some((base) => pathname === base || pathname.startsWith(`${base}/`));
}

assert.equal(isPublicPatientSurfacePath("/intake"), true);
assert.equal(isPublicPatientSurfacePath("/intake/"), true);
assert.equal(isPublicPatientSurfacePath("/consumer"), true);
assert.equal(isPublicPatientSurfacePath("/consumer/survey"), true);
assert.equal(isPublicPatientSurfacePath("/clinician"), false);

assert.equal(normalizeRequestHost("NO1KMEDI.COM:3010"), "no1kmedi.com");
assert.equal(isNo1kmediPortalHost("clinic.no1kmedi.com"), true);
assert.equal(isNo1kmediPortalHost("localhost"), false);

assert.equal(shouldRedirectRootToHubHome("app.jema-ai.com", "/", null), true);
assert.equal(shouldRedirectRootToHubHome("app.jema-ai.com", "/hub", null), false);
assert.equal(shouldRedirectRootToHubHome("app.jema-ai.com", "/", "1"), false);
assert.equal(shouldRedirectRootToHubHome("no1kmedi.com", "/", null), false);
assert.equal(shouldRewriteRootToClinician("app.jema-ai.com"), false);
assert.equal(shouldRewriteRootToClinician("no1kmedi.com"), true);

const prev = process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST;
process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST = "1";
assert.equal(shouldRewriteRootToClinician("localhost"), true);
process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST = "";
assert.equal(shouldRewriteRootToClinician("localhost"), false);
process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST = prev ?? "";

console.log("check-no1kmedi-portal-host_v1: ok");
