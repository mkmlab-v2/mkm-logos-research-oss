#!/usr/bin/env node
/**
 * HTTP smoke: POST /api/clinician/paste-extract-v1 (LLM chip extract · prod opt-in).
 *
 *   npm run smoke:clinician-paste-extract-http
 *   NO1KMEDI_BASE_URL=https://app.jema-ai.com npm run smoke:clinician-paste-extract-http
 *   PASTE_EXTRACT_HTTP_REQUIRE_LLM=1 — fail if LLM gate returns 503 disabled
 */

const BASE_URL = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");
const REQUIRE_LLM = ["1", "true", "yes", "on"].includes(
  String(process.env.PASTE_EXTRACT_HTTP_REQUIRE_LLM || "").trim().toLowerCase(),
);
const SMOKE_EMAIL = (process.env.KM_CLINICIAN_SMOKE_EMAIL || "smoke-paste-chart@local.test").trim();

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

async function request(urlPath, init) {
  const res = await fetch(`${BASE_URL}${urlPath}`, init);
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = { raw: text.slice(0, 500) };
  }
  return { res, json };
}

async function postExtract() {
  const body = {
    chart_text: "김민수 / 1988-03-12 / 남 / 36세 / 요통 3주",
  };

  return request("/api/clinician/paste-extract-v1", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: BASE_URL,
      Referer: `${BASE_URL}/clinician?panel=gold`,
      "x-clinician-email": SMOKE_EMAIL,
    },
    body: JSON.stringify(body),
  });
}

async function main() {
  let out = await postExtract();
  if (out.res.status === 422 && out.json?.error === "llm_json_parse_failed") {
    await new Promise((r) => setTimeout(r, 1500));
    out = await postExtract();
  }

  if (out.res.status === 503 && out.json?.error === "paste_extract_llm_disabled") {
    if (REQUIRE_LLM) {
      throw new Error("paste_extract_llm_disabled on server (set KM_CLINICIAN_PASTE_EXTRACT_LLM=1)");
    }
    console.log(
      JSON.stringify(
        {
          schema: "smoke_clinician_paste_extract_http_v1",
          ok: true,
          skipped: true,
          reason: "paste_extract_llm_disabled",
          base_url: BASE_URL,
        },
        null,
        2,
      ),
    );
    return;
  }

  assert(out.res.status === 200, `expected 200 got ${out.res.status}: ${out.json?.error}`);
  assert(out.json?.success === true, `success false: ${out.json?.error}`);
  assert(out.json?.draft && typeof out.json.draft === "object", "draft missing");
  assert(
    out.json.draft.display_name || out.json.draft.chief_complaint,
    "draft missing display_name or chief_complaint",
  );
  assert(out.json.human_confirm_required === true, "human_confirm_required expected true");
  assert(out.json.research_only === true, "research_only expected true");

  console.log(
    JSON.stringify(
      {
        schema: "smoke_clinician_paste_extract_http_v1",
        ok: true,
        base_url: BASE_URL,
        provider: out.json.provider || null,
        display_name: out.json.draft.display_name || null,
        confidence: out.json.draft.confidence || null,
        sources: out.json.draft.sources || [],
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error("smoke-clinician-paste-extract-http failed:", err.message);
  process.exit(1);
});
