import { chromium } from "playwright";

const BASE = "https://logos.jema-ai.com";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(`${BASE}/logos-research/studio?q=job_job_suffering_reason&autorun=1`, {
  waitUntil: "domcontentloaded",
  timeout: 120000,
});
await page.waitForSelector("#lr-studio-tab-storyboard", { timeout: 90000 });
await page.waitForTimeout(4000);
const metrics = await page.evaluate(() => ({
  scriptoriumTheme: !!document.querySelector(".logos-research-studio-theme--scriptorium"),
  inquiry: !!document.querySelector('[data-logos-scriptorium-inquiry="1"]'),
  inquiryTitle: document.querySelector(".lr-scriptorium-inquiry-title")?.textContent?.trim() ?? null,
  trustCanvas: !!document.querySelector('[data-mkm-trust-canvas="1"]'),
  storySelected: document.querySelector("#lr-studio-tab-storyboard")?.getAttribute("aria-selected"),
  mindSelected: document.querySelector("#lr-studio-tab-mindmap")?.getAttribute("aria-selected"),
  storyHidden: document.querySelector("#lr-studio-panel-storyboard")?.hasAttribute("hidden"),
  mindHidden: document.querySelector("#lr-studio-panel-mindmap")?.hasAttribute("hidden"),
  reportPanel: !!document.querySelector(".lr-scriptorium-report"),
  thinkingTitle: document.querySelector(".mkm-thinking-timeline-title")?.textContent?.trim() ?? null,
  citationEyebrow: document.querySelector(".lr-studio-citation-sidecar-eyebrow")?.textContent?.trim() ?? null,
  gridCols: document.querySelector(".mkm-trust-canvas-body")
    ? getComputedStyle(document.querySelector(".mkm-trust-canvas-body")).gridTemplateColumns
    : null,
}));
console.log(JSON.stringify(metrics, null, 2));
await browser.close();
