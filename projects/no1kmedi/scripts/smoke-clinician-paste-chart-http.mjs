#!/usr/bin/env node
/**
 * HTTP smoke: POST /api/clinician/paste-chart-v1 (ephemeral + Human Gold).
 *
 *   npm run smoke:clinician-paste-chart-http
 *   NO1KMEDI_BASE_URL=http://127.0.0.1:3010 npm run smoke:clinician-paste-chart-http
 *   PASTE_CHART_HTTP_REQUIRE_SERVE=1 npm run smoke:clinician-paste-chart-http
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BASE_URL = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");
const REQUIRE_SERVE = ["1", "true", "yes", "on"].includes(
  String(process.env.PASTE_CHART_HTTP_REQUIRE_SERVE || "").trim().toLowerCase(),
);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MONO_ROOT = path.resolve(__dirname, "../../..");
const TRACK_B = path.join(MONO_ROOT, "reports", "lee_heecheol_patient_track_b_memory_v1.json");

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

function jsonHeaders() {
  return {
    "Content-Type": "application/json",
    Origin: BASE_URL,
    Referer: `${BASE_URL}/clinician?panel=gold`,
    "x-clinician-email": "smoke-paste-chart@local.test",
  };
}

function loadLeeBirthInstant() {
  assert(fs.existsSync(TRACK_B), `track_b missing: ${TRACK_B}`);
  const doc = JSON.parse(fs.readFileSync(TRACK_B, "utf8"));
  const birthLocal = doc.profile?.birth_local;
  assert(birthLocal, "lee_heecheol birth_local missing");
  return new Date(birthLocal).toISOString();
}

async function probeServer() {
  try {
    const panel = await request("/clinician?panel=gold", { method: "GET" });
    assert(panel.res.status === 200, `panel gold status ${panel.res.status}`);
    return true;
  } catch (err) {
    if (REQUIRE_SERVE) throw err;
    console.error(
      `smoke-clinician-paste-chart-http: SKIP (server unreachable at ${BASE_URL}). Start: npm run dev`,
    );
    console.error(String(err?.message || err));
    process.exit(0);
  }
}

async function postPasteChart(label, body) {
  let out;
  try {
    out = await request("/api/clinician/paste-chart-v1", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(body),
    });
  } catch (err) {
    if (REQUIRE_SERVE) throw err;
    console.error(`smoke-clinician-paste-chart-http: SKIP (${label} fetch failed)`);
    console.error(String(err?.message || err));
    process.exit(0);
  }
  assert(out.res.status === 200, `${label}: expected 200 got ${out.res.status}: ${out.json?.error}`);
  assert(out.json?.success === true, `${label}: success false: ${out.json?.error}`);
  assert(out.json?.patient_care_bundle, `${label}: patient_care_bundle missing`);
  const soap = out.json.clinical_soap_v1 || out.json.patient_care_bundle?.clinical_soap_v1;
  assert(soap && typeof soap === "object", `${label}: clinical_soap_v1 missing`);
  return out.json;
}

async function main() {
  await probeServer();

  const ephemeral = await postPasteChart("ephemeral", {
    schema: "clinician_paste_chart_request_v1",
    display: "박신규",
    chart_text: "두통 3일 · 만성 피로 · 스트레스 증가",
    birth_instant_utc: "1985-06-15T00:00:00+09:00",
    iana_tz: "Asia/Seoul",
    is_male: true,
    allow_ephemeral: true,
    options: { validate_schema: true, validate_policy: true, render_md: false },
  });
  assert(ephemeral.ephemeral === true, "ephemeral flag expected true");
  assert(String(ephemeral.slug || "").startsWith("ephemeral_"), "ephemeral slug prefix");

  const leeBirth = loadLeeBirthInstant();
  const lee = await postPasteChart("lee_heecheol", {
    schema: "clinician_paste_chart_request_v1",
    display: "이희철",
    chart_text: "식후 더부룩함 2주 · 피로 · 야식 잦음",
    birth_instant_utc: leeBirth,
    iana_tz: "Asia/Seoul",
    is_male: true,
    allow_ephemeral: true,
    options: { validate_schema: true, validate_policy: true, render_md: false },
  });
  assert(lee.slug === "lee_heecheol", `lee slug expected lee_heecheol got ${lee.slug}`);
  assert(!lee.ephemeral, "lee_heecheol should not be ephemeral");

  console.log(
    JSON.stringify(
      {
        schema: "smoke_clinician_paste_chart_http_v1",
        ok: true,
        base_url: BASE_URL,
        ephemeral_slug: ephemeral.slug,
        lee_slug: lee.slug,
        lee_advice_error: lee.advice_error || null,
        ephemeral_advice_error: ephemeral.advice_error || null,
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error("smoke-clinician-paste-chart-http failed:", err.message);
  process.exit(1);
});
