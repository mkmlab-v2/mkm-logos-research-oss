#!/usr/bin/env node
/**
 * Smoke: GET /api/clinician/encounter-artifacts (Human Gold v0 pointer contract).
 * Requires dev server at NO1KMEDI_BASE_URL (default http://127.0.0.1:3010)
 * and MKM_WORKSPACE_ROOT pointing at monorepo with lee_heecheol pointer.
 */
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function main() {
  const url = `${BASE_URL}/api/clinician/encounter-artifacts?slug=lee_heecheol`;
  let res;
  try {
    res = await fetch(url, { cache: "no-store" });
  } catch (err) {
    throw new Error(`GET encounter-artifacts failed (${url}): ${err?.message || err}`);
  }
  const json = await res.json();
  assert(res.status === 200, `expected 200, got ${res.status}: ${JSON.stringify(json)}`);
  assert(json.success === true, "success !== true");
  assert(json.slug === "lee_heecheol", `slug mismatch: ${json.slug}`);
  assert(json.ref_token === "LEE-HEECHEOL-2026-001", `ref_token mismatch: ${json.ref_token}`);
  assert(Array.isArray(json.artifacts), "artifacts not array");
  const lifestyle = json.artifacts.find((a) => a.key === "lifestyle_management_md");
  assert(lifestyle?.exists === true, "lifestyle_management_md missing");
  assert(typeof lifestyle?.content === "string" && lifestyle.content.length > 100, "lifestyle md content short");
  assert(json.print_html_rel?.includes("lifestyle_print"), `print_html_rel: ${json.print_html_rel}`);

  const printRes = await fetch(
    `${BASE_URL}/api/clinician/encounter-artifacts/print?slug=lee_heecheol`,
    { cache: "no-store" },
  );
  const html = await printRes.text();
  assert(printRes.status === 200, `print expected 200, got ${printRes.status}`);
  assert(html.includes("<"), "print response not html");

  console.log(`smoke-clinician-encounter-artifacts: OK ${url}`);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
