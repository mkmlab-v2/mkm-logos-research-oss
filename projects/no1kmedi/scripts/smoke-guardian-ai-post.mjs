#!/usr/bin/env node
/** POST /api/guardian/ai-guardian — analysis payload contract smoke. */
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  const res = await fetch(`${BASE_URL}/api/guardian/ai-guardian`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      health_data: {
        survey: { vector_4d: { S: 0.27, L: 0.24, K: 0.23, M: 0.26 } },
        rppg: { heart_rate: 74, stress_score: 48, signal_quality: 0.92 },
        tongue: { color: "LightRed", hydrationScore: 62 },
        voice: { jitter: 0.18, shimmer: 0.12 },
      },
    }),
  });
  const json = await res.json().catch(() => ({}));

  assert(res.status === 200, `ai-guardian expected 200, got ${res.status}`);
  assert(json?.success === true, "ai-guardian success must be true");
  assert(typeof json?.analysis?.message === "string" && json.analysis.message.trim().length > 0, "analysis.message required");
  assert(Array.isArray(json?.analysis?.recommendations), "analysis.recommendations must be array");
  assert(typeof json?.analysis?.status === "string", "analysis.status required");
  assert(typeof json?.analysis?.provider_meta?.provider === "string", "provider_meta.provider required");
  assert(typeof json?.analysis?.provider_meta?.fallback_used === "boolean", "provider_meta.fallback_used boolean required");

  console.log(`smoke-guardian-ai-post passed (${BASE_URL})`);
}

main().catch((error) => {
  console.error("smoke-guardian-ai-post failed:", error.message);
  process.exit(1);
});
