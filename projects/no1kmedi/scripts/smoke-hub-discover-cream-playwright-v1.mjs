/**
 * Playwright: Hub Discover cream theme + inspector diet markers.
 *
 * Usage:
 *   HUB_DISCOVER_SMOKE_BASE=https://app.jema-ai.com node ./scripts/smoke-hub-discover-cream-playwright-v1.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const NO1K = path.resolve(__dirname, "..");
const ROOT = path.resolve(NO1K, "../..");
const BASE = (process.env.HUB_DISCOVER_SMOKE_BASE || "https://app.jema-ai.com").replace(/\/$/, "");
const STRICT = process.env.MKM_SMOKE_STRICT_PLAYWRIGHT === "1";
const OUT = path.join(ROOT, "reports", "hub_discover_cream_playwright_smoke_v1_latest.json");

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

async function main() {
  const pw = await loadPlaywright();
  if (!pw?.chromium) {
    const skip = {
      schema: "hub_discover_cream_playwright_smoke_v1",
      ok: !STRICT,
      skipped: true,
      reason: "playwright_not_installed",
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
    page.setDefaultTimeout(90000);

    step = "hub_discover_load";
    await page.goto(`${BASE}/hub`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.locator(".universe-hub-page--discover-v3").waitFor({ timeout: 60000 });
    await page.locator('[data-testid="hub-inspector-hypo-badge"]').waitFor({ timeout: 60000 });

    step = "hub_discover_cream_surface";
    const surface = await page.evaluate(() => {
      const pageEl = document.querySelector(".universe-hub-page--discover-v3");
      if (!pageEl) return { ok: false, reason: "page_missing" };
      const bg = getComputedStyle(pageEl).backgroundColor;
      const isDark =
        bg === "rgb(25, 25, 25)" ||
        bg === "rgb(25, 25, 25)" ||
        bg === "rgb(33, 33, 33)" ||
        bg === "rgb(32, 32, 32)" ||
        bg === "rgb(24, 24, 24)";
      return { ok: !isDark, backgroundColor: bg };
    });
    if (!surface.ok) {
      throw new Error(`cream_surface_fail_${JSON.stringify(surface)}`);
    }
    checks.push({ label: "hub_discover_cream_surface", ok: true, ...surface });

    step = "hub_discover_inspector_diet";
    const diet = await page.evaluate(() => {
      const summary = document.querySelector('[data-hub-inspector-discover-summary="1"]');
      const repoPaths = document.querySelectorAll(".universe-hub-artifact-path").length;
      const b2bHeading = [...document.querySelectorAll(".universe-hub-inspector-subtitle")].some(
        (el) => (el.textContent || "").includes("B2B 스포크"),
      );
      return {
        summaryPresent: !!summary,
        repoPathCount: repoPaths,
        b2bVisible: b2bHeading,
      };
    });
    if (!diet.summaryPresent || diet.repoPathCount > 0 || diet.b2bVisible) {
      throw new Error(`inspector_diet_fail_${JSON.stringify(diet)}`);
    }
    checks.push({ label: "hub_discover_inspector_diet", ok: true, ...diet });

    step = "hub_discover_gtm_folded";
    const folded = await page.evaluate(() => {
      const details = document.querySelector(".hub-discover-gtm-links-folded");
      return {
        present: !!details,
        open: details?.hasAttribute("open") ?? false,
      };
    });
    if (!folded.present || folded.open) {
      throw new Error(`gtm_fold_fail_${JSON.stringify(folded)}`);
    }
    checks.push({ label: "hub_discover_gtm_folded", ok: true, ...folded });

    const doc = {
      schema: "hub_discover_cream_playwright_smoke_v1",
      ok: true,
      base: BASE,
      checks,
      reproduce:
        "HUB_DISCOVER_SMOKE_BASE=https://app.jema-ai.com node projects/no1kmedi/scripts/smoke-hub-discover-cream-playwright-v1.mjs",
    };
    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`);
    console.log(JSON.stringify({ ok: true, checks: checks.length, out: OUT }));
  } catch (error) {
    throw new Error(`${step}: ${error instanceof Error ? error.message : String(error)}`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  const doc = {
    schema: "hub_discover_cream_playwright_smoke_v1",
    ok: false,
    error: String(error.message || error),
    base: BASE,
  };
  try {
    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`);
  } catch {
    // ignore
  }
  console.error(JSON.stringify(doc));
  process.exitCode = 1;
});
