#!/usr/bin/env node
/**
 * HTTP smoke: POST /api/clinician/encounter-sequence-v1 (park_geumja).
 * Requires Next dev with MKM_WORKSPACE_ROOT (dev unlock = no paid gate).
 *
 *   NO1KMEDI_BASE_URL=http://127.0.0.1:3022 npm run smoke:encounter-sequence-http
 */

const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function parseJson(path, res, text) {
  try {
    return JSON.parse(text);
  } catch {
    const snippet = text.replace(/\s+/g, " ").trim().slice(0, 160);
    throw new Error(`${path} non-JSON HTTP ${res.status}: ${snippet}`);
  }
}

async function main() {
  const path = "/api/clinician/encounter-sequence-v1";
  let res;
  let text;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        schema: "encounter_sequence_clinician_request_v1",
        slug: "park_geumja",
      }),
    });
    text = await res.text();
  } catch (err) {
    console.error(
      `smoke-encounter-sequence-http: FAIL (server unreachable at ${BASE_URL}). Start Next dev with MKM_WORKSPACE_ROOT.`,
    );
    console.error(String(err?.message || err));
    process.exit(1);
  }

  const json = await parseJson(path, res, text);
  assert(res.status === 200, `expected HTTP 200, got ${res.status}: ${json?.error || text.slice(0, 120)}`);
  assert(json?.success === true, `success required: ${json?.error || "unknown"}`);
  assert(json?.research_only === true, "research_only must be true");
  assert(json?.send_gate === "HOLD", "send_gate must be HOLD");
  assert(json?.encounter_sequence_id, "encounter_sequence_id required");
  assert(json?.slug === "park_geumja", `slug park_geumja required, got ${json?.slug}`);
  assert(json?.paths?.sequence_json, "paths.sequence_json required");

  console.log(
    "OK encounter-sequence HTTP:",
    json.encounter_sequence_id,
    "l0=",
    Boolean(json.l0_router_triggered),
  );
  console.log(
    JSON.stringify(
      {
        base_url: BASE_URL,
        encounter_sequence_id: json.encounter_sequence_id,
        l0_router_triggered: json.l0_router_triggered,
        display_label: json.display_label,
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error("smoke-encounter-sequence-http:", err?.message || err);
  process.exit(1);
});
