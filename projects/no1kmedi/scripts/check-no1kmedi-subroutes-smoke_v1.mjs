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
    const res = await fetch(probe.url, {
      method: "GET",
      redirect:
        probe.followRedirects
          ? "follow"
          : probe.locationIncludes || probe.locationIncludesAny
            ? "manual"
            : "follow",
      signal: AbortSignal.timeout(20000),
    });
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
    if (probe.jsonIncludes) {
      const data = JSON.parse(text);
      row.json = { ok: data.ok, preview_only: data.preview_only };
      const jsonOk = Object.entries(probe.jsonIncludes).every(([k, v]) => data[k] === v);
      if (!jsonOk) {
        row.error = "json_field_mismatch";
        report.results[probe.id] = row;
        continue;
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
