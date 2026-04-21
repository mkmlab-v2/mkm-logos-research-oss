#!/usr/bin/env node
/** POST /api/guardian/partner-clinics/chat — requires running Next (dev or start). */
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  const res = await fetch(`${BASE_URL}/api/guardian/partner-clinics/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      clinic_id: "clinic-001",
      message: "예약 안내 부탁드립니다.",
      chat_history: [],
    }),
  });
  const json = await res.json().catch(() => ({}));
  assert(res.status === 200, `partner-clinic-chat expected 200, got ${res.status}`);
  assert(json?.success === true, "partner-clinic-chat success must be true");
  assert(typeof json?.response === "string" && json.response.trim().length > 0, "non-empty response");
  assert(typeof json?.meta?.provider === "string", "meta.provider required");
  console.log(`smoke-partner-clinic-chat passed (${BASE_URL})`);
}

main().catch((error) => {
  console.error("smoke-partner-clinic-chat failed:", error.message);
  process.exit(1);
});
