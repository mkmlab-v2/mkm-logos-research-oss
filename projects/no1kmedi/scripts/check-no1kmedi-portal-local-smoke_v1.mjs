/**
 * Local smoke: no1kmedi portal host routing + minimal clinician shell markers.
 * Run: node scripts/check-no1kmedi-portal-local-smoke_v1.mjs
 * Requires dev server on NO1KMEDI_PORTAL_SMOKE_BASE (default http://localhost:3010).
 */
import assert from "node:assert/strict";

const base = (process.env.NO1KMEDI_PORTAL_SMOKE_BASE || "http://localhost:3010").replace(/\/$/, "");

async function probeApexAskRedirect() {
  const res = await fetch(`${base}/`, {
    redirect: "manual",
    headers: { Host: "no1kmedi.com" },
  });
  assert.ok([307, 308, 302, 301].includes(res.status), `apex expected redirect got ${res.status}`);
  const loc = res.headers.get("location") || "";
  assert.ok(loc.includes("/ask"), `expected /ask redirect got ${loc}`);
  return { status: res.status, location: loc };
}

async function probeClinicRootRedirect() {
  const res = await fetch(`${base}/`, {
    redirect: "manual",
    headers: { Host: "clinic.no1kmedi.com" },
  });
  assert.ok([307, 308, 302, 301].includes(res.status), `clinic expected redirect got ${res.status}`);
  const loc = res.headers.get("location") || "";
  assert.ok(loc.includes("/clinician"), `expected /clinician redirect got ${loc}`);
  return { status: res.status, location: loc };
}

async function probeClinicianMinimal() {
  const res = await fetch(`${base}/clinician`, {
    redirect: "follow",
    headers: { Host: "clinic.no1kmedi.com" },
  });
  assert.equal(res.status, 200, `clinician status ${res.status}`);
  const html = await res.text();
  assert.ok(
    /"minimalShell":true|minimalShell\\":true/.test(html),
    "minimalShell:true missing in RSC payload",
  );
  assert.ok(!html.includes("feature-triad"), "marketing feature-triad leaked into clinician");
  assert.ok(!html.includes("SINCE 1972"), "banned SINCE 1972 leaked");
  assert.ok(!html.includes("한의사를 위한 진료 보조 AI Copilot"), "legacy copilot hero leaked");
  assert.ok(html.includes("한의사 보조"), "clinician title missing");
  assert.ok(
    html.includes('data-clinician-sidebar-mode="gpt-persist"') || html.includes('data-clinician-pilot-route="v2"'),
    "clinician gpt sidebar marker missing",
  );
  return {
    status: res.status,
    minimal_shell: true,
    pilot_v1: true,
    title_ok: html.includes("한의사 보조"),
  };
}

const apex = await probeApexAskRedirect();
const clinicRoot = await probeClinicRootRedirect();
const clinician = await probeClinicianMinimal();

console.log(
  JSON.stringify(
    {
      schema: "no1kmedi_portal_local_smoke_v1",
      base,
      ok: true,
      apex,
      clinic_root: clinicRoot,
      clinician,
    },
    null,
    2,
  ),
);
