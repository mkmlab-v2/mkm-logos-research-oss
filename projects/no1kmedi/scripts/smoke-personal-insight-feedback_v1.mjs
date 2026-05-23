/**
 * Smoke: personadiary + clinician personal_insight feedback APIs.
 * Run: node scripts/smoke-personal-insight-feedback_v1.mjs
 * Env: NO1KMEDI_SMOKE_BASE_URL (default http://127.0.0.1:3010)
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(root, "../..");
const base = (process.env.NO1KMEDI_SMOKE_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");

function jsonHeaders() {
  const headers = { "content-type": "application/json" };
  const token = process.env.PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN?.trim();
  if (token) headers.authorization = `Bearer ${token}`;
  return headers;
}

async function post(path, body) {
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  const json = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, json };
}

const report = {
  schema: "no1kmedi_personal_insight_feedback_smoke_v1",
  generated_at_utc: new Date().toISOString(),
  base_url: base,
  results: {},
  ok: false,
};

const personadiary = await post("/api/personadiary/feedback", {
  helpful: true,
  surface: "daily_guide",
  profile_id: "commander",
  calendar_kst: "2026-05-20",
  consent_feedback_use: true,
  probe: true,
});
report.results.personadiary_feedback = {
  ok: personadiary.ok && personadiary.json?.ok === true,
  status: personadiary.status,
  event_id: personadiary.json?.event_id,
};

const clinician = await post("/api/cdss/physician-feedback", {
  helpful: true,
  physician_action: "accept",
  request_id: `smoke_${Date.now()}`,
  surface: "cds_draft",
  consent_feedback_use: true,
  probe: true,
});

const ingest = await post("/api/internal/personal-insight-evolution/ingest", {
  question_id: `smoke_ingest_${Date.now()}`,
  user_id: "smoke-personal-insight",
  helpful: true,
  consent_feedback_use: true,
  probe: true,
});
report.results.internal_ingest = {
  ok: ingest.ok && ingest.json?.ok === true,
  status: ingest.status,
  event_id: ingest.json?.event_id,
};
report.results.clinician_feedback = {
  ok: clinician.ok && clinician.json?.success === true,
  status: clinician.status,
  event_id: clinician.json?.event_id,
};

report.ok =
  report.results.personadiary_feedback.ok === true &&
  report.results.clinician_feedback.ok === true &&
  report.results.internal_ingest.ok === true;

const outPath = join(repoRoot, "reports/no1kmedi_personal_insight_feedback_smoke_latest.json");
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(`[smoke-personal-insight-feedback_v1] ok=${report.ok} wrote ${outPath}`);
if (!report.ok) process.exit(1);
