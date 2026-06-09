#!/usr/bin/env node
/** POST /api/clinician/eno-multimodal-intake — clinician preview contract smoke. */
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  const res = await fetch(`${BASE_URL}/api/clinician/eno-multimodal-intake`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source: "paste_json",
      health_data: {
        survey: { vector_4d: { S: 0.27, L: 0.24, K: 0.23, M: 0.26 } },
        voice: { jitter: 0.18 },
        tongue: { hydrationScore: 55 },
      },
      include_guardian_analysis: false,
    }),
  });
  const json = await res.json().catch(() => ({}));

  assert(res.status === 200, `eno-multimodal-intake expected 200, got ${res.status}`);
  assert(json?.success === true, "success must be true");
  assert(json?.human_confirm_required === true, "human_confirm_required");
  assert(json?.preview?.schema === "eno_multimodal_intake_snapshot_v1", "preview schema");
  assert(typeof json?.preview?.clinician_summary_ko === "string", "clinician_summary_ko");
  assert(json?.track === "physician_gold", "physician_gold track");

  console.log(`smoke-eno-multimodal-intake-clinician passed (${BASE_URL})`);
}

main().catch((error) => {
  console.error("smoke-eno-multimodal-intake-clinician failed:", error.message);
  process.exit(1);
});
