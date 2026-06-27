#!/usr/bin/env node
/**
 * Self-verify slash-header parse: offline regex + prod API regex_baseline + prod bundle marker.
 *
 *   node ./scripts/verify-paste-chart-slash-header-self-v1.mjs
 *   NO1KMEDI_BASE_URL=https://app.jema-ai.com KM_CLINICIAN_SMOKE_EMAIL=moksorinw@gmail.com node ./scripts/verify-paste-chart-slash-header-self-v1.mjs
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const BASE_URL = (process.env.NO1KMEDI_BASE_URL || "https://app.jema-ai.com").replace(/\/$/, "");
const SMOKE_EMAIL = (process.env.KM_CLINICIAN_SMOKE_EMAIL || "moksorinw@gmail.com").trim();
const SAMPLE_PATH = path.join(ROOT, "scripts", "fixtures", "paste-chart-sample-ko-v1.txt");

function loadSample() {
  if (!fs.existsSync(SAMPLE_PATH)) {
    throw new Error(`missing UTF-8 fixture: ${SAMPLE_PATH}`);
  }
  return fs.readFileSync(SAMPLE_PATH, "utf8").trimEnd();
}

const SAMPLE = loadSample();

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function runOfflineSmoke() {
  execFileSync("npx", ["--yes", "tsx", "./scripts/smoke-clinician-chart-paste-extract-v1.ts"], {
    cwd: ROOT,
    stdio: "inherit",
    shell: true,
  });
}

async function verifyProdRegexBaseline() {
  async function postOnce() {
    const res = await fetch(`${BASE_URL}/api/clinician/paste-extract-v1`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: BASE_URL,
        Referer: `${BASE_URL}/clinician?panel=gold`,
        "x-clinician-email": SMOKE_EMAIL,
      },
      body: JSON.stringify({ chart_text: SAMPLE }),
    });
    const json = await res.json();
    return { res, json };
  }

  let { res, json } = await postOnce();
  if (res.status === 422 && json?.error === "llm_json_parse_failed") {
    await new Promise((r) => setTimeout(r, 1500));
    ({ res, json } = await postOnce());
  }

  if (res.status === 503 && json?.error === "paste_extract_llm_disabled" && BASE_URL.includes("127.0.0.1")) {
    return {
      http_status: 503,
      api_success: false,
      api_error: "paste_extract_llm_disabled",
      note: "local dev uses client-side regex on paste (offline_smoke OK)",
      skipped_api_baseline: true,
    };
  }

  const baseline = json.regex_baseline || (json.success ? json.draft : null);
  assert(baseline, `no regex_baseline on status ${res.status}: ${json?.error}`);
  assert(baseline.display_name === "김민수", `display_name=${baseline?.display_name}`);
  assert(baseline.birthdate === "1988-03-12", `birthdate=${baseline?.birthdate}`);
  assert(baseline.sex === "M", `sex=${baseline?.sex}`);
  assert(baseline.chief_complaint?.includes("요추부"), `chief=${baseline?.chief_complaint}`);
  assert(baseline.confidence === "high", `confidence=${baseline?.confidence}`);

  return {
    http_status: res.status,
    api_success: json.success === true,
    api_error: json.error || null,
    display_name: baseline.display_name,
    birthdate: baseline.birthdate,
    sex: baseline.sex,
    chief_complaint: baseline.chief_complaint,
    confidence: baseline.confidence,
    provider: json.provider || null,
  };
}

async function verifyAccessStatus() {
  const url = `${BASE_URL}/api/member/access-status?email=${encodeURIComponent(SMOKE_EMAIL)}`;
  const res = await fetch(url);
  const json = await res.json();
  assert(res.status === 200, `access-status ${res.status}`);
  assert(json.can_use_pro_clinical_assist === true, "pro allowlist false");
  return {
    can_use_pro_clinical_assist: json.can_use_pro_clinical_assist,
    access_source: json.access_source || null,
  };
}

async function verifyProdClientBundle() {
  const panel = await fetch(`${BASE_URL}/clinician?panel=gold&email=${encodeURIComponent(SMOKE_EMAIL)}`);
  assert(panel.status === 200, `clinician panel ${panel.status}`);
  const html = await panel.text();
  assert(html.includes("_next/static") || html.includes("clinician"), "clinician page html unexpected");
  const chunkUrls = [...html.matchAll(/\/_next\/static\/chunks\/[^"']+\.js/g)].map((m) => m[0]);
  assert(chunkUrls.length > 0, "no next chunks in clinician HTML");
  let pageChunk = null;
  for (const rel of chunkUrls) {
    const js = await fetch(`${BASE_URL}${rel}`).then((r) => r.text());
    if (js.includes("pc-omni-textarea")) {
      pageChunk = rel;
      break;
    }
  }
  assert(pageChunk, "prod clinician chunk missing pc-omni-textarea");
  return { panel_status: panel.status, page_chunk: pageChunk };
}

async function main() {
  const report = {
    schema: "verify_paste_chart_slash_header_self_v1",
    ok: false,
    base_url: BASE_URL,
    smoke_email: SMOKE_EMAIL,
    checks: {},
  };

  runOfflineSmoke();
  report.checks.offline_smoke = { ok: true };

  report.checks.access_status = await verifyAccessStatus();
  report.checks.prod_regex_baseline = await verifyProdRegexBaseline();
  report.checks.prod_client_bundle = await verifyProdClientBundle();

  report.ok = true;
  console.log(JSON.stringify(report, null, 2));
}

main().catch((err) => {
  console.error(JSON.stringify({ schema: "verify_paste_chart_slash_header_self_v1", ok: false, error: err.message }, null, 2));
  process.exit(1);
});
