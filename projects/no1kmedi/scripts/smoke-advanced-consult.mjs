#!/usr/bin/env node
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";
const requireLive = process.argv.includes("--require-live") || process.env.NO1KMEDI_REQUIRE_LIVE === "1";
const requireLiterature =
  process.argv.includes("--require-literature") || process.env.NO1KMEDI_REQUIRE_LITERATURE === "1";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

/** Must stay aligned with `src/app/api/cdss/advanced-consult/route.ts` literature filter. */
function literatureInjectedCountFromDraft(draft) {
  const citations = draft?.citations;
  if (!Array.isArray(citations)) return 0;
  return citations.filter((c) => {
    const idBased = String(c.citation_id || "").startsWith("lit_");
    const refBased = String(c.source_ref || "").toLowerCase().startsWith("epmc:");
    return idBased || refBased;
  }).length;
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

function buildConsultPayload({ withRedFlags }) {
  return {
    schema: "patient_consult_input_v1",
    request_id: `smoke_${Date.now()}_${withRedFlags ? "rf" : "plain"}`,
    actor_id: "hanui-smoke-001",
    lane_a_profile: {
      birth_instant_utc: "1987-12-31T15:00:00Z",
      iana_tz: "Asia/Seoul",
      birth_datetime: "1988-01-03 06:30",
      constitution_survey: {
        digestion_pattern: "식후 더부룩함이 잦음",
        sleep_pattern: "입면 지연과 새벽 각성",
        body_heat_preference: "더위를 타고 얼굴이 달아오름",
        stress_reactivity: "긴장 시 소화가 급격히 저하됨",
        free_text: "야간 교대 근무로 생체리듬이 흔들림",
      },
    },
    lane_b_clinical: {
      chief_complaint: "만성 피로 / chronic fatigue with low back pain",
      onset: "6개월 / chronic nighttime sleep disturbance",
      severity: "중등도 / persistent pain",
      medication: "진통제 간헐 복용 / intermittent pain medication",
      health_survey: {
        sleep_quality: "중간 / poor nighttime sleep quality",
        ...(withRedFlags
          ? {
              red_flag_notes: "간헐적 흉부 불편감과 호흡곤란 느낌 / chest discomfort and dyspnea",
              appetite: "저하 / appetite reduced",
              bowel_pattern: "불규칙 / irregular bowel pattern",
            }
          : {}),
        pain_scale_0_10: 7,
      },
    },
  };
}

function assertConsultContract(consult) {
  assert(consult.res.status === 200, `advanced-consult expected 200, got ${consult.res.status}`);
  assert(consult.json?.success === true, "advanced-consult success must be true");
  assert(consult.json?.guardrail?.lane_separation === true, "lane_separation must be true");
  assert(consult.json?.guardrail?.citation_enforced === true, "citation_enforced must be true");
  assert(Array.isArray(consult.json?.draft?.citations) && consult.json.draft.citations.length > 0, "citations required");
  assert(
    consult.json?.evidence_meta?.citation_count === consult.json.draft.citations.length,
    "evidence_meta.citation_count must equal draft.citations.length",
  );
  assert(
    consult.json?.evidence_meta?.literature_injected_count === literatureInjectedCountFromDraft(consult.json.draft),
    "evidence_meta.literature_injected_count must match draft citations (lit_/epmc: rule)",
  );
  assert(typeof consult.json?.evidence_meta?.citation_count === "number", "evidence_meta.citation_count must be number");
  assert(
    typeof consult.json?.evidence_meta?.literature_injected_count === "number",
    "evidence_meta.literature_injected_count must be number",
  );
  assert(
    consult.json?.evidence_meta?.literature_count_rule_version === "v2_id_or_epmc_ref",
    "evidence_meta.literature_count_rule_version must be v2_id_or_epmc_ref",
  );
  assert(
    consult.json?.evidence_meta?.citation_count >= consult.json?.evidence_meta?.literature_injected_count,
    "literature_injected_count cannot exceed citation_count",
  );
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
}

async function main() {
  const consultWithRedFlags = await request("/api/cdss/advanced-consult", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildConsultPayload({ withRedFlags: true })),
  });

  const consultWithoutRedFlags = await request("/api/cdss/advanced-consult", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildConsultPayload({ withRedFlags: false })),
  });

  assertConsultContract(consultWithRedFlags);
  assertConsultContract(consultWithoutRedFlags);

  // Comparison guard: two channel configurations should still produce valid counts.
  assert(
    consultWithRedFlags.json?.evidence_meta?.citation_count > 0 &&
      consultWithoutRedFlags.json?.evidence_meta?.citation_count > 0,
    "both red-flag and non-red-flag scenarios must return citations",
  );

  const rfLit = literatureInjectedCountFromDraft(consultWithRedFlags.json.draft);
  const plainLit = literatureInjectedCountFromDraft(consultWithoutRedFlags.json.draft);
  const rfIds = (consultWithRedFlags.json.draft.citations || [])
    .filter((c) => String(c.citation_id || "").startsWith("lit_"))
    .map((c) => c.citation_id);
  const plainIds = (consultWithoutRedFlags.json.draft.citations || [])
    .filter((c) => String(c.citation_id || "").startsWith("lit_"))
    .map((c) => c.citation_id);
  console.log(
    `advanced-consult smoke summary: red_flag lit=${rfLit} [${rfIds.join(",")}] | plain lit=${plainLit} [${plainIds.join(",")}]`,
  );
  if (requireLiterature) {
    assert(rfLit > 0 || plainLit > 0, "require-literature enabled but no literature citations were injected");
  }

  const missingEmail = await request("/api/member/access-status", { method: "GET" });
  assert(missingEmail.res.status === 400, `member/access-status missing email expected 400, got ${missingEmail.res.status}`);

  const email = encodeURIComponent(`smoke+${Date.now()}@jema-ai.com`);
  const locked = await request(`/api/member/access-status?email=${email}`, { method: "GET" });
  assert(locked.res.status === 200, `member/access-status expected 200, got ${locked.res.status}`);
  assert(locked.json?.can_use_pro_clinical_assist === false, "new user should be locked");

  console.log(
    `smoke-advanced-consult passed (${requireLive ? "live" : "standard"}, compared red-flag/non-red-flag${
      requireLiterature ? ", literature-required" : ""
    })`,
  );
}

main().catch((error) => {
  console.error("smoke-advanced-consult failed:", error.message);
  process.exit(1);
});
