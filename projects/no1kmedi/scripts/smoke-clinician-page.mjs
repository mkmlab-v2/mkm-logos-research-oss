#!/usr/bin/env node
/**
 * Smoke: GET /clinician SSR shell (client Chat-First hydrates after load).
 * Requires dev/prod server at NO1KMEDI_BASE_URL (default http://127.0.0.1:3010).
 */
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const MARKERS = [
  "한의사 보조 · JEMA AI",
  "대화 중심 CDSS",
  "app/clinician/page",
  "ClinicianWorkspaceClient",
];

async function main() {
  let res;
  try {
    res = await fetch(`${BASE_URL}/clinician`, { cache: "no-store", redirect: "follow" });
  } catch (err) {
    throw new Error(`GET /clinician failed (${BASE_URL}): ${err?.message || err}`);
  }
  const html = await res.text();
  assert(res.status === 200, `/clinician expected 200, got ${res.status}`);
  assert(!html.includes('"statusCode":500'), "/clinician returned Next error page");
  for (const m of MARKERS) {
    assert(html.includes(m), `/clinician missing marker: ${m}`);
  }
  assert(
    html.includes("workspace-fallback") || html.includes("clinician-chat-first"),
    "/clinician missing loading shell or Chat-First root",
  );
  console.log(`smoke-clinician-page: OK ${BASE_URL}/clinician (${html.length} bytes)`);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
