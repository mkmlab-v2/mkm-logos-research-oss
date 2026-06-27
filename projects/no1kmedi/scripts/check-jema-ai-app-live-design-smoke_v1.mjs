/**
 * Live design smoke for app.jema-ai.com (hub · enterprise · clinician).
 * Env: JEMA_AI_APP_DESIGN_SMOKE_BASE (default https://app.jema-ai.com)
 *
 * Run: node scripts/check-jema-ai-app-live-design-smoke_v1.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(root, "..", "..");
const base = (process.env.JEMA_AI_APP_DESIGN_SMOKE_BASE || "https://app.jema-ai.com").replace(/\/$/, "");

const FORBIDDEN = ["47.5%", "9.1%", "100% 복원", "무손실 완성", "보장된 수익", "항상 수익"];

const PAGES = [
  {
    id: "hub",
    path: "/hub",
    required: [
      "JEMA AI",
      "Time-to-Trust",
      "무한 챗봇이 아니라",
      "면책·격벽 고지",
      "/clinician",
      "research_only",
    ],
    enhanced: ["관측·거버넌스만", "공개 관측 보드 보기"],
  },
  {
    id: "enterprise",
    path: "/enterprise",
    required: ["B2B", "jema-ai.com", "투자", "면책"],
    enhanced: ["관측·거버넌스만", "Time-to-Trust"],
  },
  {
    id: "clinician",
    path: "/clinician",
    required: ["진료", "한의"],
  },
];

function scanForbidden(body) {
  return FORBIDDEN.filter((needle) => body.includes(needle));
}

async function probePage(page) {
  const url = `${base}${page.path}`;
  const res = await fetch(url, { redirect: "follow", signal: AbortSignal.timeout(20000) });
  const body = await res.text();
  const forbidden = scanForbidden(body);
  if (page.forbidden_extra) {
    for (const f of page.forbidden_extra) {
      if (body.includes(f)) forbidden.push(f);
    }
  }
  const missingRequired = (page.required || []).filter((m) => !body.includes(m));
  const missingEnhanced = (page.enhanced || []).filter((m) => !body.includes(m));
  return {
    url,
    status: res.status,
    ok: res.ok && forbidden.length === 0 && missingRequired.length === 0,
    forbidden,
    missing_required: missingRequired,
    missing_enhanced: missingEnhanced,
  };
}

const report = {
  schema: "jema_ai_app_live_design_smoke_v1",
  generated_at_utc: new Date().toISOString(),
  base,
  overall_ok: true,
  required_ok: true,
  enhanced_ok: true,
  pages: [],
};

for (const page of PAGES) {
  try {
    const result = await probePage(page);
    report.pages.push({ id: page.id, ...result });
    if (!result.ok) report.required_ok = false;
    if (result.missing_enhanced?.length) report.enhanced_ok = false;
  } catch (e) {
    report.pages.push({ id: page.id, url: `${base}${page.path}`, ok: false, error: String(e) });
    report.required_ok = false;
  }
}

report.overall_ok = report.required_ok;

const outDir = join(repoRoot, "reports");
mkdirSync(outDir, { recursive: true });
const outPath = join(outDir, "jema_ai_app_live_design_smoke_v1_latest.json");
writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

console.log(JSON.stringify(report, null, 2));
console.log(`WROTE: ${outPath}`);

if (!report.required_ok) process.exit(1);
process.exit(0);
