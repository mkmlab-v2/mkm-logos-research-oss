/**
 * Playwright: Paste Chart analyze → chat fusion strip (web) + tauri embed hold.
 *
 * Usage:
 *   NO1KMEDI_BASE_URL=http://127.0.0.1:3010 KM_CLINICIAN_SMOKE_EMAIL=moksorinw@gmail.com node ./scripts/smoke-clinician-paste-chart-fusion-playwright-v1.mjs
 *   MKM_SMOKE_STRICT_PLAYWRIGHT=1  → fail if playwright missing
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const NO1K = path.resolve(__dirname, "..");
const ROOT = path.resolve(NO1K, "../..");
const BASE = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");
const EMAIL = (process.env.KM_CLINICIAN_SMOKE_EMAIL || "moksorinw@gmail.com").trim();
const STRICT = process.env.MKM_SMOKE_STRICT_PLAYWRIGHT === "1";
const OUT = path.join(ROOT, "reports", "clinician_paste_chart_fusion_playwright_smoke_v1_latest.json");
const FIXTURE = path.join(NO1K, "scripts", "fixtures", "paste-chart-sample-ko-v1.txt");

async function loadPlaywright() {
  const candidates = [
    path.join(NO1K, "node_modules", "playwright", "index.mjs"),
    path.join(NO1K, "node_modules", "playwright", "index.js"),
    path.join(ROOT, "node_modules", "playwright", "index.mjs"),
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

async function runPasteAnalyze(page, { embed } = {}) {
  const qs = new URLSearchParams({ panel: "gold", email: EMAIL });
  if (embed) qs.set("embed", embed);
  await page.goto(`${BASE}/clinician?${qs.toString()}`, {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });

  const textarea = page.locator(".paste-chart-omni textarea.pc-omni-textarea");
  await textarea.waitFor({ timeout: 60000 });
  const chartText = readFileSync(FIXTURE, "utf8").trimEnd();
  await textarea.fill(chartText);

  await page.locator(".pc-draft-chip-val", { hasText: "김민수" }).waitFor({ timeout: 30000 });
  await page.locator(".pc-draft-chip-val", { hasText: "1988-03-12" }).waitFor({ timeout: 30000 });

  const pipeline = page.locator(".paste-chart-omni .omni-pipeline-chips");
  await pipeline.waitFor({ timeout: 15000 });
  const pipelineCount = await pipeline.locator(".omni-pipeline-chip").count();
  if (pipelineCount < 6) {
    throw new Error(`pipeline_chip_count_expected_6 got=${pipelineCount}`);
  }

  const analyzeBtn = page.locator(".paste-chart-omni .btn-analyze");
  await analyzeBtn.waitFor({ timeout: 30000 });
  await analyzeBtn.click();

  await page.locator(".paste-chart-omni .analyze-loading").waitFor({ timeout: 30000 }).catch(() => {});
  await page.locator(".paste-chart-omni .analyze-loading").waitFor({ state: "hidden", timeout: 180000 }).catch(() => {});
  await page.locator(".paste-chart-omni .error-banner").waitFor({ state: "hidden", timeout: 5000 }).catch(() => {});
  const errText = await page.locator(".paste-chart-omni .error-banner .error-text").textContent().catch(() => null);
  if (errText?.trim()) {
    throw new Error(`paste_chart_analyze_error: ${errText.trim()}`);
  }
}

async function main() {
  const pw = await loadPlaywright();
  if (!pw?.chromium) {
    const skip = {
      schema: "clinician_paste_chart_fusion_playwright_smoke_v1",
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
  let step = "init";

  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    page.setDefaultTimeout(120000);

    step = "web_analyze_to_chat_fusion";
    await runPasteAnalyze(page);
    const pipelineOk = (await page.locator(".paste-chart-omni .omni-pipeline-chip--ok").count()) >= 3;
    checks.push({
      id: "web_pipeline_chips",
      ok: pipelineOk,
      ok_chips: await page.locator(".paste-chart-omni .omni-pipeline-chip--ok").count(),
    });
    await page.locator(".paste-chart-fusion-strip").waitFor({ timeout: 180000 });
    const fusionText = await page.locator(".paste-chart-fusion-strip").innerText();
    checks.push({
      id: step,
      ok: fusionText.toLowerCase().includes("paste chart") && fusionText.includes("김민수"),
      fusion_preview: fusionText.split("\n").slice(0, 3).join(" | "),
    });

    step = "web_chat_assistant_turn";
    await page.locator(".chat-log .chat-bubble-assistant").first().waitFor({ timeout: 60000 });
    const assistantCount = await page.locator(".chat-log .chat-bubble-assistant").count();
    checks.push({ id: step, ok: assistantCount >= 1, assistant_turns: assistantCount });

    step = "tauri_embed_stays_on_gold";
    const tauriPage = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    tauriPage.setDefaultTimeout(120000);
    await runPasteAnalyze(tauriPage, { embed: "tauri" });
    await tauriPage.locator(".paste-chart-omni").waitFor({ timeout: 180000 });
    const tauriFusionVisible = await tauriPage.locator(".paste-chart-fusion-strip").isVisible().catch(() => false);
    const omniVisible = await tauriPage.locator(".paste-chart-omni").isVisible();
    checks.push({
      id: step,
      ok: omniVisible && !tauriFusionVisible,
      omni_visible: omniVisible,
      fusion_visible: tauriFusionVisible,
    });
    await tauriPage.close();

    const ok = checks.every((c) => c.ok);
    const report = {
      schema: "clinician_paste_chart_fusion_playwright_smoke_v1",
      ok,
      base: BASE,
      email: EMAIL,
      checks,
      reproduce: `NO1KMEDI_BASE_URL=${BASE} KM_CLINICIAN_SMOKE_EMAIL=${EMAIL} node projects/no1kmedi/scripts/smoke-clinician-paste-chart-fusion-playwright-v1.mjs`,
    };
    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(OUT, `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify(report, null, 2));
    if (!ok) process.exitCode = 1;
  } catch (err) {
    const fail = {
      schema: "clinician_paste_chart_fusion_playwright_smoke_v1",
      ok: false,
      step,
      error: err instanceof Error ? err.message : String(err),
      checks,
      base: BASE,
    };
    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(OUT, `${JSON.stringify(fail, null, 2)}\n`);
    console.error(JSON.stringify(fail, null, 2));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
