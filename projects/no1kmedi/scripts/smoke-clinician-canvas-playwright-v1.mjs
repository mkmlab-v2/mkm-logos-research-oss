/**
 * Playwright: Clinician Trust Canvas stub (empty + shell markers).
 *
 * Usage:
 *   CLINICIAN_CANVAS_SMOKE_BASE=https://app.jema-ai.com node ./scripts/smoke-clinician-canvas-playwright-v1.mjs
 *   MKM_SMOKE_STRICT_PLAYWRIGHT=1  → fail if playwright missing
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const NO1K = path.resolve(__dirname, "..");
const ROOT = path.resolve(NO1K, "../..");
const BASE = (process.env.CLINICIAN_CANVAS_SMOKE_BASE || "https://app.jema-ai.com").replace(/\/$/, "");
const STRICT = process.env.MKM_SMOKE_STRICT_PLAYWRIGHT === "1";
const OUT = path.join(ROOT, "reports", "clinician_canvas_playwright_smoke_v1_latest.json");
const CDS_FIXTURE = path.join(ROOT, "tests/fixtures/km_physician_cds_assist_envelope_v1.example.json");
const STORAGE_KEY = "jema_ai_clinician_threads_v1";

function buildFilledThreadSeed(envelope) {
  const now = Date.now();
  return {
    v: 1,
    threads: [
      {
        id: "cl_playwright_park_geumja_v1",
        title: "박금자 · 데모",
        patientLabel: "박금자",
        sessionDate: "2026-06-26",
        titlePinned: true,
        createdAt: now,
        updatedAt: now,
        turns: [{ role: "user", message: "만성 피로와 수면 장애가 3개월째입니다." }],
        context: {
          actorId: "hanui-demo-001",
          birthInstantUtc: "1990-01-01T00:00:00Z",
          ianaTz: "Asia/Seoul",
          chiefComplaint: "만성 피로",
          onset: "3개월",
          severity: "중등도",
          medication: "",
          digestionPattern: "",
          sleepPattern: "불면",
          bodyHeatPreference: "",
          stressReactivity: "",
          constitutionFreeText: "",
          painScale0to10: "5",
          redFlagNotes: "",
          healthAppetite: "",
          healthBowelPattern: "",
          loadedSurveyContext: null,
          enoMultimodalIntake: null,
          lensMode: "neutral",
          includeScripture: false,
        },
        lastCds: {
          requestId: "cds_playwright_park_geumja_v1",
          clinicalSummary: "Playwright CDS envelope filled-state smoke (park_geumja demo).",
          reasoning: {
            syndrome_hypothesis: "기허 혈허 의심",
            care_direction: "보기 중심 상담",
            caution: "응급 징후 시 대면 평가",
          },
          envelope,
          validationOk: true,
        },
      },
    ],
  };
}

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
      schema: "clinician_canvas_playwright_smoke_v1",
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

    step = "clinician_canvas_empty";
    await page.goto(`${BASE}/clinician?panel=copilot&canvas=1`, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });

    await page.locator('[data-clinician-canvas-placeholder="1"]').waitFor({ timeout: 60000 });
    await page.locator('[data-mkm-trust-canvas="1"]').waitFor({ timeout: 60000 });
    await page.locator('[data-mkm-trust-canvas-domain="clinician"]').waitFor({ timeout: 60000 });
    await page.locator('[data-mkm-thinking-timeline="1"]').waitFor({ timeout: 60000 });

    await page.waitForFunction(
      () =>
        !!document.querySelector(
          '[data-mkm-trust-canvas-citation-dock="1"] [data-clinician-citation-lock="1"]',
        ),
      { timeout: 60000 },
    );

    const metrics = await page.evaluate(() => {
      const shell = document.querySelector('[data-mkm-trust-canvas="1"]');
      const body = shell?.querySelector(".mkm-trust-canvas-body");
      const chat = shell?.querySelector(".mkm-trust-canvas-chat");
      const main = shell?.querySelector(".mkm-trust-canvas-main");
      const dock = document.querySelector('[data-mkm-trust-canvas-citation-dock="1"]');
      const lock = document.querySelector('[data-clinician-citation-lock="1"]');
      const placeholderCanvas = document.querySelector('[data-clinician-canvas-placeholder-canvas="1"]');
      return {
        domain: shell?.getAttribute("data-mkm-trust-canvas-domain"),
        empty: document.querySelector('[data-clinician-canvas-empty="1"]') != null,
        trustCanvas: !!shell,
        gridBody: !!body,
        chatPane: !!chat,
        mainPane: !!main,
        thinking: !!document.querySelector('[data-mkm-thinking-timeline="1"]'),
        citationDock: !!dock,
        citationLock: !!lock,
        placeholderCanvas: !!placeholderCanvas,
        scopeLabel: document.querySelector(".mkm-trust-canvas-scope-label")?.textContent?.trim() || "",
      };
    });

    if (metrics.domain !== "clinician") {
      throw new Error(`domain_not_clinician_${metrics.domain}`);
    }
    if (!metrics.trustCanvas || !metrics.gridBody || !metrics.chatPane || !metrics.mainPane) {
      throw new Error(`shell_grid_missing_${JSON.stringify(metrics)}`);
    }
    if (!metrics.citationDock || !metrics.citationLock) {
      throw new Error(`citation_dock_missing_${JSON.stringify(metrics)}`);
    }
    if (!metrics.placeholderCanvas) {
      throw new Error("placeholder_canvas_missing");
    }
    checks.push({ label: "clinician_canvas_empty_shell", ok: true, ...metrics });

    step = "clinician_canvas_scope_tags";
    const tagCount = await page.evaluate(
      () => document.querySelectorAll(".mkm-trust-canvas-scope-tags li").length,
    );
    if (tagCount < 2) {
      throw new Error(`scope_tags_too_few_${tagCount}`);
    }
    checks.push({ label: "clinician_canvas_scope_tags", ok: true, tagCount });

    step = "clinician_canvas_hold_tag";
    const holdTag = await page.evaluate(() => {
      const hold = document.querySelector('.mkm-trust-canvas-scope-tags li[data-tag-hold="1"]');
      return {
        present: !!hold,
        text: hold?.textContent?.trim() || "",
      };
    });
    if (!holdTag.present) {
      throw new Error("scope_hold_tag_missing");
    }
    checks.push({ label: "clinician_canvas_hold_tag", ok: true, ...holdTag });

    step = "clinician_canvas_dark_surface";
    const surfaceTone = await page.evaluate(() => {
      const shell = document.querySelector(
        ".clinician-canvas-page.clinician-canvas-theme .mkm-trust-canvas",
      );
      if (!shell) return { ok: false, reason: "shell_missing" };
      const bg = getComputedStyle(shell).backgroundColor;
      const isWhite = bg === "rgb(255, 255, 255)" || bg === "white";
      return { ok: !isWhite, backgroundColor: bg };
    });
    if (!surfaceTone.ok) {
      throw new Error(`dark_surface_fail_${JSON.stringify(surfaceTone)}`);
    }
    checks.push({ label: "clinician_canvas_dark_surface", ok: true, ...surfaceTone });

    step = "clinician_demo_patient_api";
    const demoRes = await fetch(`${BASE}/api/clinician/demo-patient?slug=park_geumja`);
    const demoJson = await demoRes.json().catch(() => ({}));
    if (demoRes.status === 200 && demoJson?.success === true) {
      checks.push({
        label: "clinician_demo_patient_park_geumja",
        ok: true,
        slug: demoJson?.slug || demoJson?.context_patch?.ssotSlug || "park_geumja",
      });
    } else if (demoRes.status === 401) {
      checks.push({
        label: "clinician_demo_patient_park_geumja",
        ok: true,
        skipped: true,
        reason: "pro_auth_required_on_live",
        status: demoRes.status,
      });
    } else {
      throw new Error(`demo_patient_api_fail_${demoRes.status}`);
    }

    step = "clinician_canvas_filled_cds_envelope";
    const envelope = JSON.parse(readFileSync(CDS_FIXTURE, "utf8"));
    const filledSeed = buildFilledThreadSeed(envelope);
    const filledPage = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    filledPage.setDefaultTimeout(90000);
    await filledPage.addInitScript(
      ({ key, payload }) => {
        localStorage.setItem(key, JSON.stringify(payload));
      },
      { key: STORAGE_KEY, payload: filledSeed },
    );
    await filledPage.goto(`${BASE}/clinician?panel=copilot&canvas=1`, {
      waitUntil: "domcontentloaded",
      timeout: 120000,
    });
    await filledPage.locator('[data-clinician-canvas-studio="1"]').waitFor({ timeout: 60000 });
    const filledMetrics = await filledPage.evaluate(() => {
      const studio = document.querySelector('[data-clinician-canvas-studio="1"]');
      const empty = document.querySelector('[data-clinician-canvas-empty="1"]');
      const graph = document.querySelector(".clinician-canvas-graph-panel");
      const conflict = document.querySelector(".clinician-canvas-conflict-sheet");
      const lock = document.querySelector('[data-clinician-citation-lock="1"]');
      return {
        studio: !!studio,
        empty: !!empty,
        graphPanel: !!graph,
        conflictSheet: !!conflict,
        citationLock: !!lock,
        validation: lock?.getAttribute("data-clinician-citation-validation") || "",
        requestId: lock?.getAttribute("data-clinician-citation-request-id") || "",
        patientLabel: document.querySelector(".mkm-trust-canvas-scope-label")?.textContent?.trim() || "",
      };
    });
    if (!filledMetrics.studio || filledMetrics.empty) {
      throw new Error(`filled_studio_missing_${JSON.stringify(filledMetrics)}`);
    }
    if (!filledMetrics.graphPanel || !filledMetrics.conflictSheet) {
      throw new Error(`filled_panels_missing_${JSON.stringify(filledMetrics)}`);
    }
    if (!filledMetrics.citationLock || filledMetrics.validation !== "ok") {
      throw new Error(`filled_citation_lock_${JSON.stringify(filledMetrics)}`);
    }
    checks.push({ label: "clinician_canvas_filled_cds_envelope", ok: true, ...filledMetrics });

    step = "clinician_graph_build_e2e";
    const buildResponsePromise = filledPage.waitForResponse(
      (res) =>
        res.url().includes("/api/clinician/graph/build-from-cds") && res.request().method() === "POST",
      { timeout: 90000 },
    );
    await filledPage.getByRole("button", { name: "그래프 생성" }).click();
    const buildResponse = await buildResponsePromise;
    const buildJson = await buildResponse.json().catch(() => ({}));
    if (!buildResponse.ok() || buildJson?.success !== true) {
      throw new Error(`graph_build_api_fail_${buildResponse.status()}_${JSON.stringify(buildJson).slice(0, 200)}`);
    }
    await filledPage.locator(".consult-graph-node-list li").first().waitFor({ timeout: 60000 });
    const graphMetrics = await filledPage.evaluate(() => {
      const items = document.querySelectorAll(".consult-graph-node-list li");
      const summary =
        document.querySelector(".clinician-canvas-graph-panel .notice-box p")?.textContent?.trim() || "";
      return {
        nodeListCount: items.length,
        summary,
        hasListViewBtn: !!document.querySelector('.workspace-secondary-btn.is-active'),
      };
    });
    if (graphMetrics.nodeListCount < 1) {
      throw new Error(`graph_nodes_missing_${JSON.stringify(graphMetrics)}`);
    }
    const apiNodeCount = Array.isArray(buildJson?.graph_bundle_v1?.nodes)
      ? buildJson.graph_bundle_v1.nodes.length
      : 0;
    if (apiNodeCount < 1) {
      throw new Error(`graph_api_nodes_missing_${apiNodeCount}`);
    }
    checks.push({
      label: "clinician_graph_build_e2e",
      ok: true,
      apiNodeCount,
      edgeCount: Array.isArray(buildJson?.graph_bundle_v1?.edges) ? buildJson.graph_bundle_v1.edges.length : 0,
      ...graphMetrics,
    });
    await filledPage.close();

    const doc = {
      schema: "clinician_canvas_playwright_smoke_v1",
      ok: true,
      base: BASE,
      checks,
      reproduce:
        "CLINICIAN_CANVAS_SMOKE_BASE=https://app.jema-ai.com node projects/no1kmedi/scripts/smoke-clinician-canvas-playwright-v1.mjs",
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
    schema: "clinician_canvas_playwright_smoke_v1",
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
