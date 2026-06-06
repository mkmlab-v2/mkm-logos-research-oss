/**
 * Pilot commercial bundle smoke — design tokens, disclaimer, a11y markers.
 * Run: node scripts/check-clinician-pilot-commercial-smoke_v1.mjs
 * Env: CLINICIAN_PILOT_SMOKE_BASE (default https://app.jema-ai.com)
 */
import assert from "node:assert/strict";

const base = (process.env.CLINICIAN_PILOT_SMOKE_BASE || "https://app.jema-ai.com").replace(/\/$/, "");

async function probeClinicianPilot() {
  const res = await fetch(`${base}/clinician`, { redirect: "follow" });
  assert.equal(res.status, 200, `clinician status ${res.status}`);
  const html = await res.text();

  const checks = {
    minimal_shell: /"minimalShell":true|minimalShell\\":true/.test(html),
    pilot_route: html.includes('data-clinician-pilot-route="v2"') || html.includes('data-clinician-sidebar-mode="gpt-persist"'),
    gpt_sidebar: html.includes('data-clinician-sidebar="gpt-persist"') || html.includes('data-clinician-sidebar-mode="gpt-persist"'),
    clinician_title: html.includes("한의사 보조"),
    safety_meta: html.includes("최종 진단") || html.includes("참고·초안"),
    no_marketing_leak: !html.includes("SINCE 1972") && !html.includes("feature-triad"),
  };

  for (const [key, ok] of Object.entries(checks)) {
    assert.ok(ok, `check failed: ${key}`);
  }

  return { status: res.status, checks };
}

const clinician = await probeClinicianPilot();

console.log(
  JSON.stringify(
    {
      schema: "clinician_pilot_commercial_smoke_v1",
      base,
      ok: true,
      clinician,
    },
    null,
    2,
  ),
);
