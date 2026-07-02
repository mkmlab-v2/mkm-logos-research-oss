/**
 * Smoke: personadiary + smartfarm preview routes (edge or local BASE_URL).
 * Run from projects/no1kmedi: node scripts/check-no1kmedi-subroutes-smoke_v1.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(root, "../..");
const base = (process.env.NO1KMEDI_SMOKE_BASE_URL || "https://jema-ai.com").replace(/\/$/, "");

const probes = [
  {
    id: "safety_lane_governance_page",
    url: `${(process.env.NO1KMEDI_APP_SMOKE_BASE_URL || "https://app.jema-ai.com").replace(/\/$/, "")}/safety`,
    expectStatus: 200,
    bodyIncludes: ["도메인 혼선 방지", "공개 레인 라우팅 표", "Article 1.3"],
  },
  {
    id: "safety_lanes_alias_redirect",
    url: `${(process.env.NO1KMEDI_APP_SMOKE_BASE_URL || "https://app.jema-ai.com").replace(/\/$/, "")}/lanes`,
    expectStatus: 308,
    locationIncludes: "/safety",
  },
  {
    id: "validation_ring1_page",
    url: `${(process.env.NO1KMEDI_APP_SMOKE_BASE_URL || "https://app.jema-ai.com").replace(/\/$/, "")}/validation`,
    expectStatus: 200,
    bodyIncludes: ["검증", "Ring 1"],
  },
  {
    id: "personadiary_page",
    url: `${base}/personadiary`,
    expectStatus: 200,
    bodyIncludes: ["Persona Diary", "프리뷰", "안전·면책"],
  },
  {
    id: "smartfarm_app_hub_redirect",
    url: "https://app.jema-ai.com/smartfarm",
    expectStatuses: [301, 302, 308],
    locationIncludesAny: ["farm.jema-ai.com"],
  },
  {
    id: "smartfarm_apex_chain",
    url: `${base}/smartfarm`,
    followRedirects: true,
    finalUrlIncludes: "farm.jema-ai.com",
  },
  {
    id: "smartfarm_farm_host",
    url: "https://farm.jema-ai.com/",
    expectStatus: 200,
    bodyIncludes: ["MKM", "금산"],
  },
  {
    id: "personadiary_daily_guide_api",
    url: `${base}/api/personadiary/daily-guide`,
    expectStatus: 200,
    jsonIncludes: { ok: true, preview_only: true },
  },
  {
    id: "personadiary_apex_page",
    url: "https://personadiary.com/",
    headers: { "User-Agent": "MKM-PersonadiarySmoke/1.0" },
    expectStatus: 200,
    bodyIncludes: ["Persona Diary", "프리뷰"],
  },
  {
    id: "personadiary_moment_api",
    method: "POST",
    url: "https://personadiary.com/api/personadiary/moment",
    headers: {
      "User-Agent": "MKM-PersonadiarySmoke/1.0",
      "content-type": "application/json",
    },
    body: { text: "오늘 점심 뭐 먹을까?" },
    expectStatus: 200,
    jsonIncludes: { ok: true },
    jsonMomentIntent: "meal",
  },
  {
    id: "personadiary_feedback_api",
    method: "POST",
    url: `${(process.env.NO1KMEDI_FEEDBACK_SMOKE_BASE_URL || "https://app.jema-ai.com").replace(/\/$/, "")}/api/personadiary/feedback`,
    body: {
      helpful: true,
      surface: "daily_guide",
      profile_id: "commander",
      probe: true,
      consent_feedback_use: true,
    },
    expectStatus: 200,
    jsonIncludes: { ok: true, preview_only: true },
  },
];

const report = {
  schema: "no1kmedi_subroutes_smoke_v1",
  generated_at_utc: new Date().toISOString(),
  base_url: base,
  deploy_triggered: false,
  git_push: false,
  results: {},
  ok: false,
};

for (const probe of probes) {
  const row = { url: probe.url, ok: false };
  try {
    const method = probe.method || "GET";
    const fetchInit = {
      method,
      redirect:
        probe.followRedirects
          ? "follow"
          : probe.locationIncludes || probe.locationIncludesAny
            ? "manual"
            : "follow",
      signal: AbortSignal.timeout(20000),
    };
    fetchInit.headers = { ...(probe.headers || {}) };
    if (method === "POST" && probe.body) {
      fetchInit.headers["content-type"] =
        fetchInit.headers["content-type"] || "application/json";
      fetchInit.body = JSON.stringify(probe.body);
    }
    const res = await fetch(probe.url, fetchInit);
    row.status = res.status;
    const text = await res.text();
    row.content_type = res.headers.get("content-type");
    if (probe.followRedirects) {
      row.final_url = res.url;
      if (res.url.includes(probe.finalUrlIncludes)) {
        row.ok = true;
      } else {
        row.error = "final_url_mismatch";
      }
      report.results[probe.id] = row;
      continue;
    }
    if (probe.locationIncludesAny) {
      const loc = res.headers.get("location") || "";
      row.location = loc;
      const statusOk = (probe.expectStatuses || [probe.expectStatus]).includes(res.status);
      const locOk = probe.locationIncludesAny.some((h) => loc.includes(h));
      if (statusOk && locOk) {
        row.ok = true;
      } else {
        row.error = "redirect_mismatch";
      }
      report.results[probe.id] = row;
      continue;
    }
    if (probe.locationIncludes) {
      const loc = res.headers.get("location") || "";
      row.location = loc;
      if (res.status === probe.expectStatus && loc.includes(probe.locationIncludes)) {
        row.ok = true;
      } else {
        row.error = "redirect_mismatch";
      }
      report.results[probe.id] = row;
      continue;
    }
    if (res.status !== probe.expectStatus) {
      row.error = `expected_status_${probe.expectStatus}`;
      report.results[probe.id] = row;
      continue;
    }
    if (probe.jsonIncludes || probe.jsonMomentIntent) {
      const data = JSON.parse(text);
      row.json = { ok: data.ok, preview_only: data.preview_only };
      if (probe.jsonIncludes) {
        const jsonOk = Object.entries(probe.jsonIncludes).every(([k, v]) => data[k] === v);
        if (!jsonOk) {
          row.error = "json_field_mismatch";
          report.results[probe.id] = row;
          continue;
        }
      }
      if (probe.jsonMomentIntent) {
        const intent = data?.moment?.intent;
        row.json.moment_intent = intent;
        if (intent !== probe.jsonMomentIntent) {
          row.error = "moment_intent_mismatch";
          report.results[probe.id] = row;
          continue;
        }
      }
    }
    if (probe.bodyIncludes) {
      const missing = probe.bodyIncludes.filter((s) => !text.includes(s));
      if (missing.length) {
        row.error = "body_missing";
        row.missing = missing;
        report.results[probe.id] = row;
        continue;
      }
    }
    row.ok = true;
    report.results[probe.id] = row;
  } catch (e) {
    row.error = String(e);
    report.results[probe.id] = row;
  }
}

report.ok = Object.values(report.results).every((r) => r.ok === true);

const outPath = join(repoRoot, "reports", "no1kmedi_subroutes_smoke_latest.json");
mkdirSync(join(repoRoot, "reports"), { recursive: true });
writeFileSync(outPath, JSON.stringify(report, null, 2), "utf8");

console.log(JSON.stringify(report, null, 2));
console.log(`\n[check-no1kmedi-subroutes-smoke_v1] wrote ${outPath}`);
process.exit(report.ok ? 0 : 1);
