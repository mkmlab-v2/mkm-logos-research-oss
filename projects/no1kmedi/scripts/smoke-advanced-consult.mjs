#!/usr/bin/env node
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";
const requireLive = process.argv.includes("--require-live") || process.env.NO1KMEDI_REQUIRE_LIVE === "1";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function request(path, init) {
  const res = await fetch(`${BASE_URL}${path}`, init);
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = { raw: text };
  }
  return { res, json };
}

async function main() {
  const consult = await request("/api/cdss/advanced-consult", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      schema: "patient_consult_input_v1",
      request_id: `smoke_${Date.now()}`,
      actor_id: "hanui-smoke-001",
      lane_a_profile: {
        birth_instant_utc: "1987-12-31T15:00:00Z",
        iana_tz: "Asia/Seoul",
        birth_datetime: "1988-01-03 06:30",
        constitution_survey: {
          digestion_pattern: "식후 더부룩함이 잦음",
          sleep_pattern: "입면 지연과 새벽 각성",
        },
      },
      lane_b_clinical: {
        chief_complaint: "만성 피로",
        onset: "6개월",
        severity: "중등도",
        medication: "없음",
        health_survey: { sleep_quality: "중간" },
      },
    }),
  });

  assert(consult.res.status === 200, `advanced-consult expected 200, got ${consult.res.status}`);
  assert(consult.json?.success === true, "advanced-consult success must be true");
  assert(consult.json?.guardrail?.lane_separation === true, "lane_separation must be true");
  assert(consult.json?.guardrail?.citation_enforced === true, "citation_enforced must be true");
  assert(Array.isArray(consult.json?.draft?.citations) && consult.json.draft.citations.length > 0, "citations required");
  const gen = consult.json?.draft?.generation;
  assert(typeof gen?.llm_used === "boolean", "draft.generation.llm_used must be boolean");
  if (gen.llm_used === false) {
    assert(typeof gen.reason === "string" && gen.reason.length > 0, "draft.generation.reason required when llm_used is false");
  }

  const source = consult.json?.draft?.profile_summary?.saju_source;
  assert(source === "live" || source === "fallback", `invalid saju_source: ${source}`);
  if (requireLive) {
    assert(source === "live", "saju_source must be live in --require-live mode");
  }

  const missingEmail = await request("/api/member/access-status", { method: "GET" });
  assert(missingEmail.res.status === 400, `member/access-status missing email expected 400, got ${missingEmail.res.status}`);

  const email = encodeURIComponent(`smoke+${Date.now()}@no1kmedi.com`);
  const locked = await request(`/api/member/access-status?email=${email}`, { method: "GET" });
  assert(locked.res.status === 200, `member/access-status expected 200, got ${locked.res.status}`);
  assert(locked.json?.can_use_pro_clinical_assist === false, "new user should be locked");

  console.log(`smoke-advanced-consult passed (${requireLive ? "live" : "standard"})`);
}

main().catch((error) => {
  console.error("smoke-advanced-consult failed:", error.message);
  process.exit(1);
});
