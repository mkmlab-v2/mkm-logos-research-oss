#!/usr/bin/env node
/**
 * Auto local Paste Chart: offline extract + POST paste-chart-v1 + SOAP S shape gate.
 *
 *   node ./scripts/verify-paste-chart-auto-local-v1.mjs
 *   NO1KMEDI_BASE_URL=http://127.0.0.1:3010 KM_CLINICIAN_SMOKE_EMAIL=moksorinw@gmail.com node ./scripts/verify-paste-chart-auto-local-v1.mjs
 */

import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const BASE_URL = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");
const EMAIL = (process.env.KM_CLINICIAN_SMOKE_EMAIL || "moksorinw@gmail.com").trim();

const SAMPLE = `김민수 / 1988-03-12 / 남 / 36세 / 요통 3주

[주소] 서울 강남
[CC] 요추부 통증, 3주 전부터 악화. 앉아 있을 때 더 아픔.
[Hx] 진통제 병력`;

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function birthdateToBirthInstantUtc(birthdate) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(birthdate).trim());
  if (!m) return null;
  return new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00+09:00`).toISOString();
}

function runOfflineSmoke() {
  execFileSync("npx", ["--yes", "tsx", "./scripts/smoke-clinician-chart-paste-extract-v1.ts"], {
    cwd: ROOT,
    stdio: "inherit",
    shell: true,
  });
}

function validateSoapSubjective(text) {
  const raw = String(text || "");
  assert(raw.includes("호소·증상"), "SOAP S missing 호소·증상");
  assert(raw.includes("요추부"), "SOAP S missing CC chief");
  const headerHits = (raw.match(/김민수\s*\/\s*1988-03-12/g) || []).length;
  assert(headerHits <= 1, `SOAP S repeats slash header ${headerHits}x`);
  assert(raw.includes("현재 상황"), "SOAP S missing 현재 상황");
  const situationLine = raw.split("\n").find((l) => l.includes("현재 상황")) || "";
  assert(situationLine.includes("김민수"), "situation missing name");
  assert(!situationLine.includes("[CC]"), "situation must not include [CC] block");
}

async function postPasteChart() {
  const birthInstant = birthdateToBirthInstantUtc("1988-03-12");
  assert(birthInstant, "birth instant missing");

  const res = await fetch(`${BASE_URL}/api/clinician/paste-chart-v1`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: BASE_URL,
      Referer: `${BASE_URL}/clinician?panel=gold`,
      "x-clinician-email": EMAIL,
    },
    body: JSON.stringify({
      schema: "clinician_paste_chart_request_v1",
      chart_text: SAMPLE,
      display: "김민수",
      allow_ephemeral: true,
      birth_instant_utc: birthInstant,
      iana_tz: "Asia/Seoul",
      is_male: true,
      options: { validate_schema: true, validate_policy: true, render_md: true },
    }),
  });
  const json = await res.json();
  return { res, json };
}

async function main() {
  runOfflineSmoke();

  const { res, json } = await postPasteChart();
  assert(res.status === 200, `paste-chart status ${res.status}: ${json?.error}`);
  assert(json.success === true, `paste-chart failed: ${json?.error}`);

  const soap = json.patient_care_bundle?.clinical_soap_v1;
  const subj = soap?.subjective?.text || "";
  validateSoapSubjective(subj);

  console.log(
    JSON.stringify(
      {
        schema: "verify_paste_chart_auto_local_v1",
        ok: true,
        base_url: BASE_URL,
        email: EMAIL,
        ephemeral: Boolean(json.ephemeral),
        soap_s_preview: subj.split("\n").slice(0, 6).join("\n"),
        advice_error: json.advice_error || null,
      },
      null,
      2,
    ),
  );
}

main().catch((err) => {
  console.error(JSON.stringify({ schema: "verify_paste_chart_auto_local_v1", ok: false, error: err.message }, null, 2));
  process.exit(1);
});
