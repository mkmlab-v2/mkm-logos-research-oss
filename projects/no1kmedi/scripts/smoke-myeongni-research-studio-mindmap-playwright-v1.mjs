/**
 * Playwright: Myeongni research studio path mindmap (demo mode).
 *
 * Usage:
 *   NO1KMEDI_BASE_URL=http://127.0.0.1:3020 node ./scripts/smoke-myeongni-research-studio-mindmap-playwright-v1.mjs
 *   MKM_SMOKE_STRICT_PLAYWRIGHT=1  → fail if playwright missing
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const NO1K = path.resolve(__dirname, "..");
const ROOT = path.resolve(NO1K, "../..");
const BASE = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3020").replace(/\/$/, "");
const STRICT = process.env.MKM_SMOKE_STRICT_PLAYWRIGHT === "1";
const OUT = path.join(ROOT, "reports", "myeongni_studio_mindmap_playwright_smoke_v1_latest.json");

async function loadPlaywright() {
  const candidates = [
    path.join(NO1K, "node_modules", "playwright", "index.mjs"),
    path.join(NO1K, "node_modules", "playwright", "index.js"),
    path.join(ROOT, "node_modules", "playwright", "index.mjs"),
    path.join(ROOT, "projects", "mkm", "mkm-life", "node_modules", "playwright", "index.mjs"),
  ];
  for (const candidate of candidates) {
    try {
      return await import(pathToFileURL(candidate).href);
    } catch {
      // try next
    }
  }
  try {
    return await import("playwright");
  } catch {
    return null;
  }
}

async function assertMindmapVisible(page, label) {
  const mindmap = page.locator('[data-myeongni-path-mindmap="1"]').first();
  await mindmap.waitFor({ state: "visible", timeout: 90000 });
  const box = await mindmap.boundingBox();
  if (!box || box.width < 80 || box.height < 80) {
    throw new Error(`${label}_mindmap_bbox_too_small`);
  }
  const metrics = await page.evaluate(() => {
    const panel = document.querySelector('[data-myeongni-path-mindmap="1"]');
    const svg = panel?.querySelector("svg");
    const circles = svg ? svg.querySelectorAll("circle").length : 0;
    const nodeAttr = panel?.getAttribute("data-myeongni-mindmap-node-count");
    const nodeCount = nodeAttr ? Number(nodeAttr) : 0;
    return { circles, nodeCount };
  });
  if (metrics.circles < 8) {
    throw new Error(`${label}_node_circles_too_few_${metrics.circles}`);
  }
  if (metrics.nodeCount < 8) {
    throw new Error(`${label}_node_count_attr_${metrics.nodeCount}`);
  }
  return { label, width: box.width, height: box.height, ...metrics };
}

async function main() {
  const pw = await loadPlaywright();
  if (!pw?.chromium) {
    const skip = {
      schema: "myeongni_studio_mindmap_playwright_smoke_v1",
      ok: !STRICT,
      skipped: true,
      reason: "playwright_not_installed",
      hint: "cd projects/no1kmedi && npm i -D playwright && npx playwright install chromium",
      base: BASE,
    };
    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(OUT, `${JSON.stringify(skip, null, 2)}\n`);
    console.log(JSON.stringify(skip));
    process.exitCode = STRICT ? 1 : 0;
    return;
  }

  const browser = await pw.chromium.launch({ headless: true });
  const checks = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(`${BASE}/myeongni-research/studio`, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });
    await page.locator('[data-myeongni-studio-shell="1"]').waitFor({ timeout: 60000 });
    checks.push(await assertMindmapVisible(page, "studio_demo"));

    await page.getByRole("tab", { name: "엔진 (verify-lite)" }).click();
    await page.getByRole("button", { name: "엔진 조회 → 마인드맵" }).click();
    await page.locator('[data-myeongni-path-mindmap="1"]').waitFor({ state: "visible", timeout: 120000 });
    checks.push(await assertMindmapVisible(page, "studio_engine"));
  } finally {
    await browser.close();
  }

  const report = {
    schema: "myeongni_studio_mindmap_playwright_smoke_v1",
    ok: true,
    base: BASE,
    checks,
    reproduce: `NO1KMEDI_BASE_URL=${BASE} node projects/no1kmedi/scripts/smoke-myeongni-research-studio-mindmap-playwright-v1.mjs`,
  };
  mkdirSync(path.dirname(OUT), { recursive: true });
  writeFileSync(OUT, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ ok: true, checks: checks.length, out: OUT }));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
