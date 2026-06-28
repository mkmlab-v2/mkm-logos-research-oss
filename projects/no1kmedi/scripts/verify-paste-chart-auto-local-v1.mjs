#!/usr/bin/env node
/**
 * Auto local Paste Chart: offline extract + POST paste-chart-v1 + SOAP S shape gate.
 *
 *   node ./scripts/verify-paste-chart-auto-local-v1.mjs
 *   NO1KMEDI_BASE_URL=http://127.0.0.1:3010 KM_CLINICIAN_SMOKE_EMAIL=moksorinw@gmail.com node ./scripts/verify-paste-chart-auto-local-v1.mjs
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const BASE_URL = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");
const EMAIL = (process.env.KM_CLINICIAN_SMOKE_EMAIL || "moksorinw@gmail.com").trim();
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
  const ccHits = (raw.match(/요추부 통증, 3주 전부터 악화/g) || []).length;
  assert(ccHits === 1, `SOAP S repeats CC chief ${ccHits}x`);
  assert(raw.includes("현재 상황"), "SOAP S missing 현재 상황");
  const symptomLine = raw.split("\n").find((l) => l.includes("호소·증상")) || "";
  assert(!symptomLine.includes("[주소]"), "symptoms must not include address tag");
  assert(!symptomLine.includes("[Hx]"), "symptoms must not include Hx tag");
  const situationLine = raw.split("\n").find((l) => l.includes("현재 상황")) || "";
  assert(situationLine.includes("김민수"), "situation missing name");
  assert(situationLine.includes("서울"), "situation missing address");
  assert(!situationLine.includes("[CC]"), "situation must not include [CC] block");
  const notesLine = raw.split("\n").find((l) => l.startsWith("- 기타:")) || "";
  assert(!notesLine.includes("[CC]"), "notes must not duplicate CC block");
  assert(notesLine.includes("[Hx]") || notesLine.includes("진통제"), "notes missing Hx");
}

const SAMPLE6 =
  "김민정 1988.06.25 양력 서울 오후 4시 출생 여자 168에 58키로  혈압 120에 83/ 최근 불면, 설진상 습울, 상열, 안면 홍조, , 불면, 두통/ 생리통, 복직근 긴장. 중완 압통, 때떄로 타이레놀 복용/ 흉곽 예각 설하정맥 얇은 편, 수족 냉한 편/ 소음인 추정/";

async function postPasteChart(body) {
  const res = await fetch(`${BASE_URL}/api/clinician/paste-chart-v1`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: BASE_URL,
      Referer: `${BASE_URL}/clinician?panel=gold&email=${encodeURIComponent(EMAIL)}`,
      "x-clinician-email": EMAIL,
    },
    body: JSON.stringify({
      schema: "clinician_paste_chart_request_v1",
      allow_ephemeral: true,
      iana_tz: "Asia/Seoul",
      options: { validate_schema: true, validate_policy: false, render_md: true },
      ...body,
    }),
  });
  const json = await res.json();
  return { res, json };
}

function validateAdviceCoherence(adviceBlock, adviceError) {
  assert(!adviceError, `advice_error: ${adviceError}`);
  assert(adviceBlock?.cards, "advice.cards missing");

  const items = adviceBlock.cards.tcm_primary?.items || [];
  const titles = items.map((i) => String(i.title || ""));
  const lifestylePolicy = items.filter((i) => i.tier === "POLICY" || i.tier === "ACTION");
  const checklist = adviceBlock.cards.physician_checklist?.items || [];

  assert(!titles.includes("주소"), 'advice must not use mislabeled slot title "주소"');
  assert(titles.includes("주증상"), "advice missing 주증상 context card");
  assert(!checklist.some((line) => String(line).startsWith("제외 권고:")), "suppression must not appear in checklist");

  for (const item of lifestylePolicy) {
    assert(!String(item.title || "").includes("성장기"), `policy/action title: ${item.title}`);
    assert(!String(item.body || "").includes("성장기"), `policy/action body: ${item.title}`);
  }
}

function validatePasteChartPayload(json, { expectSasangKo = false } = {}) {
  const soap = json.patient_care_bundle?.clinical_soap_v1;
  validateAdviceCoherence(json.advice, json.advice_error);
  const checklist = json.advice?.cards?.physician_checklist?.items || [];
  assert(!checklist.some((line) => String(line).startsWith("제외 권고:")), "suppression must not appear in checklist");
  const assessment = soap?.assessment?.text || "";
  if (expectSasangKo) {
    assert(assessment.includes("소음인"), "SOAP A missing 소음인 when chart hints soeum");
    assert(!assessment.includes("**미입력**"), "SOAP A still 미입력 when soeum hinted");
  }
  return {
    suppression_count: json.advice?.cards?.iws_suppression_log?.length ?? 0,
    assessment_line: assessment.split("\n")[1] || "",
    advice_titles: (json.advice?.cards?.tcm_primary?.items || []).map((i) => i.title).slice(0, 8),
  };
}

async function main() {
  runOfflineSmoke();

  const birthInstant = birthdateToBirthInstantUtc("1988-03-12");
  assert(birthInstant, "birth instant missing");

  const { res, json } = await postPasteChart({
    chart_text: SAMPLE,
    display: "김민수",
    birth_instant_utc: birthInstant,
    is_male: true,
  });
  assert(res.status === 200, `paste-chart status ${res.status}: ${json?.error}`);
  assert(json.success === true, `paste-chart failed: ${json?.error}`);

  const subj = json.patient_care_bundle?.clinical_soap_v1?.subjective?.text || "";
  validateSoapSubjective(subj);
  const kimMinsoo = validatePasteChartPayload(json);

  const birthInstant6 = birthdateToBirthInstantUtc("1988-06-25");
  assert(birthInstant6, "kim minjeong birth instant missing");
  const res6 = await postPasteChart({
    chart_text: SAMPLE6,
    display: "김민정",
    birth_instant_utc: birthInstant6,
    is_male: false,
  });
  assert(res6.res.status === 200, `kim minjeong status ${res6.res.status}: ${res6.json?.error}`);
  assert(res6.json.success === true, `kim minjeong failed: ${res6.json?.error}`);
  const kimMinjeong = validatePasteChartPayload(res6.json, { expectSasangKo: true });
  assert(res6.json.display_label?.includes("김민정") || res6.json.slug, "kim minjeong encounter missing");

  console.log(
    JSON.stringify(
      {
        schema: "verify_paste_chart_auto_local_v1",
        ok: true,
        base_url: BASE_URL,
        email: EMAIL,
        ephemeral: Boolean(json.ephemeral),
        soap_s_preview: subj.split("\n").slice(0, 6).join("\n"),
        kim_minsoo: kimMinsoo,
        kim_minjeong: kimMinjeong,
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
