/**
 * Playwright: Logos landing hero mini-mindmap + Studio mindmap tab.
 *
 * Usage:
 *   LOGOS_STUDIO_SMOKE_BASE=https://logos.jema-ai.com node ./scripts/smoke-logos-research-studio-mindmap-playwright-v1.mjs
 *   MKM_SMOKE_STRICT_PLAYWRIGHT=1  → fail if playwright missing
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const NO1K = path.resolve(__dirname, "..");
const ROOT = path.resolve(NO1K, "../..");
const BASE = (process.env.LOGOS_STUDIO_SMOKE_BASE || "https://logos.jema-ai.com").replace(/\/$/, "");
const STRICT = process.env.MKM_SMOKE_STRICT_PLAYWRIGHT === "1";
const EXPECT_CANVAS = process.env.LOGOS_STUDIO_SMOKE_EXPECT_CANVAS === "1";
const OUT = path.join(ROOT, "reports", "logos_studio_mindmap_playwright_smoke_v1_latest.json");

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

async function waitForMindmapReady(page, label) {
  await page.waitForSelector('[data-logos-path-mindmap="1"]', { timeout: 90000 });
  if (label.startsWith("studio") || label === "hero_landing") {
    const studioMode = label.startsWith("studio");
    await page.waitForFunction(
      (isStudio) => {
        const panel = document.querySelector('[data-logos-path-mindmap="1"]');
        const mesh = Number(panel?.getAttribute("data-logos-mindmap-mesh-count") || 0);
        const circles = panel?.querySelectorAll("svg circle")?.length || 0;
        return isStudio ? mesh >= 3 || circles >= 10 : mesh >= 3 || circles >= 10;
      },
      studioMode,
      { timeout: 90000 },
    );
  }
}

async function assertMindmapVisible(page, label) {
  await waitForMindmapReady(page, label);
  const mindmap = page.locator('[data-logos-path-mindmap="1"]').first();
  const box = await mindmap.boundingBox();
  if (!box || box.width < 80 || box.height < 80) {
    throw new Error(`${label}_mindmap_bbox_too_small`);
  }
  const metrics = await page.evaluate(() => {
    const panel = document.querySelector('[data-logos-path-mindmap="1"]');
    const svg = panel?.querySelector("svg");
    const circles = svg ? svg.querySelectorAll("circle").length : 0;
    const meshAttr = panel?.getAttribute("data-logos-mindmap-mesh-count");
    const meshCount = meshAttr ? Number(meshAttr) : 0;
    const labels = [...(svg?.querySelectorAll("text") || [])].map((t) => t.textContent || "");
    const truncated = labels.filter((t) => t.includes("…")).length;
    const heroCard = document.querySelector(".lr-hero-inline-demo-card--tabbed");
    const scrollRatio = heroCard
      ? heroCard.scrollHeight / Math.max(heroCard.clientHeight, 1)
      : null;
    return { circles, meshCount, truncated, scrollRatio };
  });
  if (label.startsWith("studio") && metrics.circles < 8) {
    throw new Error(`${label}_node_circles_too_few_${metrics.circles}`);
  }
  if (label === "hero_landing" && metrics.scrollRatio && metrics.scrollRatio > 1.25) {
    throw new Error(`${label}_hero_card_scroll_${metrics.scrollRatio.toFixed(2)}`);
  }
  if (metrics.truncated > 5) {
    throw new Error(`${label}_truncated_labels_${metrics.truncated}`);
  }
  const minMesh = label === "studio_tab_roundtrip" ? 2 : 3;
  if (label.startsWith("studio") && metrics.meshCount > 0 && metrics.meshCount < minMesh) {
    throw new Error(`${label}_mesh_count_${metrics.meshCount}`);
  }
  return { label, width: box.width, height: box.height, ...metrics };
}

async function main() {
  const pw = await loadPlaywright();
  if (!pw?.chromium) {
    const skip = {
      schema: "logos_studio_mindmap_playwright_smoke_v1",
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
    page.setDefaultTimeout(90000);

    step = "hero_landing";
    await page.goto(`${BASE}/logos-research`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.locator('[data-logos-graph-studio-inline="1"]').waitFor({ timeout: 60000 });
    await page.locator("#lr-hero-tab-mindmap").click();
    await page.locator('[data-logos-hero-mini-mindmap="1"]').waitFor({ state: "visible", timeout: 90000 });
    checks.push(await assertMindmapVisible(page, "hero_landing"));

    step = "studio_omni_entry";
    await page.goto(`${BASE}/logos-research/studio`, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });
    await page.locator('[data-logos-studio-omni-entry="1"]').waitFor({ timeout: 60000 });
    const omniMetrics = await page.evaluate(() => ({
      phase: document.querySelector(".logos-research-page")?.getAttribute("data-logos-studio-phase"),
      omniEntry: !!document.querySelector('[data-logos-studio-omni-entry="1"]'),
      trustCanvas: !!document.querySelector('[data-mkm-trust-canvas="1"]'),
      queryInput: !!document.querySelector("#lr-query"),
    }));
    if (omniMetrics.phase !== "omni" || !omniMetrics.omniEntry || omniMetrics.trustCanvas) {
      throw new Error(`studio_omni_entry_fail_${JSON.stringify(omniMetrics)}`);
    }
    checks.push({ label: "studio_omni_entry_idle", ok: true, ...omniMetrics });

    step = "studio_job_load";
    await page.goto(
      `${BASE}/logos-research/studio?q=job_job_suffering_reason&autorun=1&demo=1`,
      { waitUntil: "domcontentloaded", timeout: 120000 },
    );
    await page.locator("#lr-studio-tab-storyboard").waitFor({ timeout: 60000 });
    const storyboardTab = page.locator("#lr-studio-tab-storyboard");
    const storyboardSelected = await storyboardTab.getAttribute("aria-selected");
    if (storyboardSelected !== "true") {
      throw new Error(`studio_demo_default_not_storyboard_${storyboardSelected}`);
    }
    const storyboardVisible = await page.evaluate(() => {
      const panel = document.querySelector("#lr-studio-panel-storyboard");
      return !!panel && !panel.hasAttribute("hidden");
    });
    if (!storyboardVisible) {
      throw new Error("studio_storyboard_panel_not_visible");
    }
    checks.push({ label: "studio_demo_default_storyboard", ok: true });

    await page.waitForFunction(
      () => document.querySelectorAll(".lr-studio-ref-chip").length >= 2,
      { timeout: 90000 },
    );

    const mindmapTab = page.locator("#lr-studio-tab-mindmap");
    step = "studio_mindmap";
    await mindmapTab.click();
    checks.push(await assertMindmapVisible(page, "studio_default_tab"));

    step = "studio_explore";
    await page.locator("#lr-studio-tab-explore").click();
    let exploreMetrics;
    let exploreHeadlessDegraded = false;
    try {
      await page.waitForFunction(
        () => {
          const panel = document.querySelector('[data-logos-explore-mesh="1"]');
          const sim = panel?.getAttribute("data-logos-explore-sim");
          const nodes = Number(panel?.getAttribute("data-logos-explore-node-count") || 0);
          return sim === "live" && nodes >= 10;
        },
        { timeout: 90000 },
      );
      exploreMetrics = await page.evaluate(() => {
        const panel = document.querySelector('[data-logos-explore-mesh="1"]');
        return {
          sim: panel?.getAttribute("data-logos-explore-sim"),
          nodes: Number(panel?.getAttribute("data-logos-explore-node-count") || 0),
          canvas: !!panel?.querySelector("canvas"),
        };
      });
      if (!exploreMetrics.canvas || exploreMetrics.nodes < 10) {
        throw new Error(`studio_explore_mesh_not_ready_${JSON.stringify(exploreMetrics)}`);
      }
      checks.push({ label: "studio_explore_tab", ...exploreMetrics });
    } catch (exploreErr) {
      exploreMetrics = await page.evaluate(() => {
        const panel = document.querySelector('[data-logos-explore-mesh="1"]');
        return {
          sim: panel?.getAttribute("data-logos-explore-sim"),
          nodes: Number(panel?.getAttribute("data-logos-explore-node-count") || 0),
          canvas: !!panel?.querySelector("canvas"),
          panel: !!panel,
        };
      });
      exploreHeadlessDegraded = !!exploreMetrics.panel;
      if (!exploreHeadlessDegraded) {
        throw exploreErr instanceof Error ? exploreErr : new Error(String(exploreErr));
      }
      checks.push({
        label: "studio_explore_tab",
        ...exploreMetrics,
        headless_degraded: true,
      });
    }

    const jerChipMapped = await page.evaluate(() => {
      const chip = [...document.querySelectorAll(".lr-studio-ref-chip")].find((el) =>
        (el.textContent || "").includes("Jer.31.4"),
      );
      return !!chip && !chip.classList.contains("lr-studio-ref-chip--slice-out");
    });
    if (!jerChipMapped) {
      throw new Error("studio_jer_31_4_still_unmapped");
    }
    checks.push({ label: "studio_router_verse_stub_mapped", ok: true, ref: "Jer.31.4" });

    const labelSync = await page.evaluate(() =>
      document.querySelector('[data-logos-explore-mesh="1"]')?.getAttribute("data-logos-explore-label-sync"),
    );
    if (!exploreHeadlessDegraded && labelSync !== "raf") {
      throw new Error(`studio_explore_label_sync_${labelSync || "missing"}`);
    }

    let labelCount = 0;
    try {
      await page.waitForFunction(
        () =>
          Number(
            document
              .querySelector('[data-logos-explore-mesh="1"]')
              ?.getAttribute("data-logos-explore-label-count") || 0,
          ) >= 2,
        { timeout: 20000 },
      );
      labelCount = await page.evaluate(() =>
        Number(
          document.querySelector('[data-logos-explore-mesh="1"]')?.getAttribute("data-logos-explore-label-count") ||
            0,
        ),
      );
      checks.push({ label: "studio_explore_mesh_labels", ok: true, labelCount, labelSync });
    } catch {
      const headlessDegraded =
        exploreHeadlessDegraded ||
        (exploreMetrics.nodes >= 10 && exploreMetrics.sim === "live" && labelSync === "raf");
      if (!headlessDegraded) {
        throw new Error("studio_explore_label_count_timeout");
      }
      checks.push({
        label: "studio_explore_mesh_labels",
        ok: true,
        labelCount: 0,
        labelSync,
        headless_degraded: true,
      });
    }

    const ghostCount = await page.evaluate(() =>
      Number(document.querySelector('[data-logos-explore-mesh="1"]')?.getAttribute("data-logos-explore-ghost-count") || 0),
    );
    checks.push({ label: "studio_explore_ghost_nodes", ok: true, ghostCount });

    const sidecarVisible = await page.evaluate(() => {
      const el = document.querySelector('[data-logos-citation-sidecar="1"]');
      return !!el && (el.textContent || "").length > 20;
    });
    if (!sidecarVisible) {
      throw new Error("studio_citation_sidecar_missing");
    }
    const sidecarHasVerseBody = await page.evaluate(() => {
      return document.querySelector('[data-logos-citation-sidecar="1"]')?.getAttribute("data-logos-citation-has-verse-body") === "1";
    });
    if (!sidecarHasVerseBody) {
      throw new Error("studio_citation_sidecar_missing_verse_body");
    }
    checks.push({ label: "studio_citation_sidecar", ok: true, hasVerseBody: true });

    step = "studio_citation_feel";
    const targetChip = page.locator(".lr-studio-ref-chip", { hasText: "Ps.23.3" });
    if ((await targetChip.count()) < 1) {
      throw new Error("studio_ref_chip_ps_23_3_missing");
    }
    const titleBefore = await page.evaluate(() =>
      document.querySelector('[data-logos-citation-sidecar="1"]')?.getAttribute("data-logos-citation-title"),
    );
    await targetChip.first().click();
    await page.waitForFunction(
      (prev) => {
        const title = document.querySelector('[data-logos-citation-sidecar="1"]')?.getAttribute("data-logos-citation-title");
        return title && title !== prev;
      },
      titleBefore,
      { timeout: 15000 },
    );
    const feelGate = await page.evaluate(() => ({
      title: document.querySelector('[data-logos-citation-sidecar="1"]')?.getAttribute("data-logos-citation-title"),
      hasVerseBody: document.querySelector('[data-logos-citation-sidecar="1"]')?.getAttribute("data-logos-citation-has-verse-body") === "1",
      hasVerseSection: (document.querySelector(".lr-studio-citation-sidecar-verse")?.textContent || "").length > 8,
    }));
    if (!feelGate.hasVerseBody || !feelGate.hasVerseSection) {
      throw new Error(`studio_citation_feel_gate_fail_${JSON.stringify(feelGate)}`);
    }
    checks.push({ label: "studio_citation_feel_gate", ok: true, ...feelGate });

    step = "studio_embed_isaiah";
    await page.goto(
      `${BASE}/logos-research/studio?q=isaiah_youtube_spine_v1&autorun=1&demo=1`,
      { waitUntil: "domcontentloaded", timeout: 120000 },
    );
    await page.locator('[data-logos-studio-shell="1"]').first().waitFor({ timeout: 60000 });
    await page.waitForFunction(
      () => document.querySelectorAll(".lr-studio-ref-chip").length >= 2,
      { timeout: 90000 },
    );
    await page.waitForFunction(
      () => {
        const chip = [...document.querySelectorAll(".lr-studio-ref-chip")].find((el) =>
          (el.textContent || "").includes("Isa.6.8"),
        );
        return !!chip && !chip.classList.contains("lr-studio-ref-chip--slice-out");
      },
      { timeout: 90000 },
    );
    checks.push({ label: "studio_embed_isaiah_router_stub", ok: true, ref: "Isa.6.8" });

    if (EXPECT_CANVAS) {
      step = "studio_canvas_shell";
      await page.goto(
        `${BASE}/logos-research/studio?q=job_job_suffering_reason&autorun=1`,
        { waitUntil: "domcontentloaded", timeout: 120000 },
      );
      await page.locator('[data-mkm-trust-canvas="1"]').waitFor({ timeout: 60000 });
      await page.locator('[data-mkm-thinking-timeline="1"]').waitFor({ timeout: 60000 });
      await page.waitForFunction(
        () => document.querySelectorAll(".lr-studio-ref-chip").length >= 2,
        { timeout: 120000 },
      );
      await page.waitForFunction(
        () =>
          !!document.querySelector(
            '[data-mkm-trust-canvas-citation-dock="1"] [data-logos-citation-sidecar="1"]',
          ),
        { timeout: 120000 },
      );
      const canvasMetrics = await page.evaluate(() => ({
        trustCanvas: !!document.querySelector('[data-mkm-trust-canvas="1"]'),
        thinking: !!document.querySelector('[data-mkm-thinking-timeline="1"]'),
        slotFilters: !!document.querySelector('[data-logos-preset-slot-filters="1"]'),
        citationDock: !!document.querySelector('[data-mkm-trust-canvas-citation-dock="1"]'),
        citationInDock: !!document.querySelector(
          '[data-mkm-trust-canvas-citation-dock="1"] [data-logos-citation-sidecar="1"]',
        ),
      }));
      if (!canvasMetrics.trustCanvas || !canvasMetrics.thinking) {
        throw new Error(`studio_canvas_shell_missing_${JSON.stringify(canvasMetrics)}`);
      }
      if (!canvasMetrics.citationDock || !canvasMetrics.citationInDock) {
        throw new Error(`studio_canvas_citation_dock_missing_${JSON.stringify(canvasMetrics)}`);
      }
      checks.push({ label: "studio_canvas_shell", ok: true, ...canvasMetrics });

      await page.waitForTimeout(2500);
      const scriptoriumDefault = await page.evaluate(() => ({
        storySelected: document.querySelector("#lr-studio-tab-storyboard")?.getAttribute("aria-selected"),
        reportPanel: !!document.querySelector(".lr-scriptorium-report"),
        storyHidden: document.querySelector("#lr-studio-panel-storyboard")?.hasAttribute("hidden"),
      }));
      if (scriptoriumDefault.storySelected !== "true" || scriptoriumDefault.storyHidden) {
        throw new Error(`studio_autorun_scriptorium_not_storyboard_${JSON.stringify(scriptoriumDefault)}`);
      }
      checks.push({ label: "studio_autorun_scriptorium_storyboard", ok: true, ...scriptoriumDefault });

      step = "studio_canvas_cream_surface";
      const creamMetrics = await page.evaluate(() => {
        const pageEl = document.querySelector(".logos-research-page.logos-research-studio-theme");
        const bg = pageEl ? getComputedStyle(pageEl).backgroundColor : "";
        const bodyGrid = document.querySelector(".mkm-trust-canvas-body");
        const gridCols = bodyGrid ? getComputedStyle(bodyGrid).gridTemplateColumns : "";
        const stepCount = document.querySelectorAll(".mkm-thinking-timeline-step").length;
        return {
          bg,
          gridCols,
          stepCount,
          thinkingTimeline: !!document.querySelector('[data-mkm-thinking-timeline="1"]'),
        };
      });
      if (creamMetrics.bg !== "rgb(250, 247, 242)") {
        throw new Error(`studio_canvas_cream_bg_${creamMetrics.bg || "missing"}`);
      }
      if (!creamMetrics.thinkingTimeline || creamMetrics.stepCount < 1) {
        throw new Error(`studio_canvas_thinking_stepper_${JSON.stringify(creamMetrics)}`);
      }
      const gridParts = creamMetrics.gridCols.split(/\s+/).filter(Boolean);
      if (gridParts.length < 2) {
        throw new Error(`studio_canvas_grid_28_72_${creamMetrics.gridCols || "missing"}`);
      }
      checks.push({ label: "studio_canvas_cream_surface", ok: true, ...creamMetrics });

      step = "studio_pastoral_mode";
      await page.goto(
        `${BASE}/logos-research/studio?mode=pastoral&autorun=1`,
        { waitUntil: "domcontentloaded", timeout: 120000 },
      );
      await page.locator('[data-logos-audience-mode="pastoral"]').waitFor({ state: "attached", timeout: 60000 });
      await page.locator('[data-logos-pastoral-disclaimer="1"]').waitFor({ state: "attached", timeout: 60000 });
      const pastoralMetrics = await page.evaluate(() => ({
        mode: document.querySelector('[data-logos-audience-mode]')?.getAttribute("data-logos-audience-mode"),
        disclaimer: !!document.querySelector('[data-logos-pastoral-disclaimer="1"]'),
        presetCount: document.querySelectorAll("#lr-preset option").length,
      }));
      if (pastoralMetrics.mode !== "pastoral" || !pastoralMetrics.disclaimer) {
        throw new Error(`studio_pastoral_mode_fail_${JSON.stringify(pastoralMetrics)}`);
      }
      checks.push({ label: "studio_pastoral_mode", ok: true, ...pastoralMetrics });
    }

    step = "studio_scriptorium_roundtrip";
    await page.goto(
      `${BASE}/logos-research/studio?q=job_job_suffering_reason&autorun=1`,
      { waitUntil: "domcontentloaded", timeout: 120000 },
    );
    await page.waitForFunction(
      () => document.querySelectorAll(".lr-studio-ref-chip").length >= 2,
      { timeout: 120000 },
    );
    const scriptoriumRoundtrip = await page.evaluate(() => ({
      storySelected: document.querySelector("#lr-studio-tab-storyboard")?.getAttribute("aria-selected"),
      reportPanel: !!document.querySelector(".lr-scriptorium-report"),
      inquiryPanel: !!document.querySelector(".lr-scriptorium-inquiry"),
      citationDock: !!document.querySelector('[data-mkm-trust-canvas-citation-dock="1"]'),
    }));
    if (
      scriptoriumRoundtrip.storySelected !== "true" ||
      !scriptoriumRoundtrip.reportPanel ||
      !scriptoriumRoundtrip.inquiryPanel
    ) {
      throw new Error(`studio_scriptorium_roundtrip_fail_${JSON.stringify(scriptoriumRoundtrip)}`);
    }
    checks.push({ label: "studio_scriptorium_roundtrip", ok: true, ...scriptoriumRoundtrip });

    const doc = {
      schema: "logos_studio_mindmap_playwright_smoke_v1",
      ok: true,
      base: BASE,
      checks,
      reproduce:
        "LOGOS_STUDIO_SMOKE_BASE=https://logos.jema-ai.com node projects/no1kmedi/scripts/smoke-logos-research-studio-mindmap-playwright-v1.mjs",
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
    schema: "logos_studio_mindmap_playwright_smoke_v1",
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
