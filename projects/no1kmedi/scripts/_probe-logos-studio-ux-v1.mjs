/**
 * One-off UX probe: sidecar content + verse click + explore focus.
 * node projects/no1kmedi/scripts/_probe-logos-studio-ux-v1.mjs
 */
import { writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../../..");
const OUT = path.join(ROOT, "reports", "logos_studio_ux_probe_v1_latest.json");
const BASE = (process.env.LOGOS_STUDIO_SMOKE_BASE || "https://logos.jema-ai.com").replace(/\/$/, "");

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {
    return null;
  }
}

async function main() {
  const pw = await loadPlaywright();
  if (!pw?.chromium) {
    console.error(JSON.stringify({ ok: false, reason: "playwright_missing" }));
    process.exit(1);
  }

  const browser = await pw.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  await page.goto(
    `${BASE}/logos-research/studio?q=job_job_suffering_reason&autorun=1&demo=1`,
    { waitUntil: "domcontentloaded", timeout: 120000 },
  );
  await page.waitForTimeout(9000);

  const readSidecar = () =>
    page.evaluate(() => {
      const el = document.querySelector('[data-logos-citation-sidecar="1"]');
      const text = el?.textContent || "";
      return {
        title: el?.getAttribute("data-logos-citation-title") || null,
        charLen: text.length,
        hasPathNote: text.includes("경로 해설"),
        hasPathSteps: text.includes("경로 단계"),
        hasVerseBody: text.includes("본문") || text.includes("개역") || text.includes("우리"),
        excerpt: text.replace(/\s+/g, " ").trim().slice(0, 320),
        activeTab: document.querySelector('[role="tab"][aria-selected="true"]')?.id || null,
      };
    });

  const init = await readSidecar();
  const versePills = await page.evaluate(() =>
    [...document.querySelectorAll(".lr-studio-verse-pill--btn")].map((x) => (x.textContent || "").trim()),
  );

  let afterClick = null;
  const chips = page.locator(".lr-studio-verse-pill--btn");
  const chipCount = await chips.count();
  if (chipCount > 1) {
    await chips.nth(1).click();
    await page.waitForTimeout(1800);
    afterClick = await readSidecar();
  }

  await page.locator("#lr-studio-tab-explore").click();
  await page.waitForFunction(
    () => {
      const p = document.querySelector('[data-logos-explore-mesh="1"]');
      return p?.getAttribute("data-logos-explore-sim") === "live";
    },
    { timeout: 60000 },
  );
  await page.waitForTimeout(2000);

  const explore = await page.evaluate(() => {
    const p = document.querySelector('[data-logos-explore-mesh="1"]');
    return {
      sim: p?.getAttribute("data-logos-explore-sim"),
      nodes: Number(p?.getAttribute("data-logos-explore-node-count") || 0),
      focusId: p?.getAttribute("data-logos-explore-focus-id") || null,
      canvas: !!p?.querySelector("canvas"),
    };
  });

  await browser.close();

  const doc = {
    schema: "logos_studio_ux_probe_v1",
    ok: true,
    base: BASE,
    init,
    versePills,
    afterClick,
    explore,
    verdict: {
      sidecar_has_content: (init?.charLen || 0) > 50,
      verse_click_changes_title:
        afterClick && init && afterClick.title !== init.title,
      explore_live: explore.sim === "live" && explore.canvas,
      missing_verse_body: !(afterClick?.hasVerseBody || init?.hasVerseBody),
    },
    reproduce: "node projects/no1kmedi/scripts/_probe-logos-studio-ux-v1.mjs",
  };

  mkdirSync(path.dirname(OUT), { recursive: true });
  writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`);
  console.log(JSON.stringify(doc));
}

main().catch((e) => {
  console.error(JSON.stringify({ ok: false, error: String(e.message || e) }));
  process.exit(1);
});
