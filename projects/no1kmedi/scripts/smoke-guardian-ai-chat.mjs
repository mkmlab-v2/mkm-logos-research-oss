#!/usr/bin/env node
/** POST /api/guardian/ai-guardian/chat — requires running Next (same as smoke-partner-clinic-chat). */
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  const res = await fetch(`${BASE_URL}/api/guardian/ai-guardian/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: "수면이 얕아졌어요. 한의 관점에서 참고할 점만 짧게 알려주세요.",
      health_data: {
        survey: {
          vector_4d: { S: 0.22, L: 0.28, K: 0.25, M: 0.25 },
        },
      },
      chat_history: [],
    }),
  });
  const json = await res.json().catch(() => ({}));
  assert(res.status === 200, `ai-guardian/chat expected 200, got ${res.status}`);
  assert(json?.success === true, "ai-guardian/chat success must be true");
  assert(typeof json?.response === "string" && json.response.trim().length > 0, "non-empty response");
  assert(typeof json?.meta?.provider === "string", "meta.provider required");
  assert(typeof json?.meta?.fallback_used === "boolean", "meta.fallback_used must be boolean");
  console.log(`smoke-guardian-ai-chat passed (${BASE_URL})`);
}

main().catch((error) => {
  console.error("smoke-guardian-ai-chat failed:", error.message);
  process.exit(1);
});
