/**
 * Playwright: /logos-research/ask inquiry beta — hybrid P0-1b (snapshot S1–S3 + S4 stream + S5 seal).
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const NO1K = path.resolve(__dirname, "..");
const ROOT = path.resolve(NO1K, "../..");
const BASE = (() => {
  const eq = process.argv.find((a) => a.startsWith("--base="));
  if (eq) return eq.slice(7).replace(/\/$/, "");
  const idx = process.argv.indexOf("--base");
  if (idx >= 0 && process.argv[idx + 1] && !process.argv[idx + 1].startsWith("-")) {
    return process.argv[idx + 1].replace(/\/$/, "");
  }
  return (process.env.LOGOS_ASK_SMOKE_BASE || "http://127.0.0.1:3010").replace(/\/$/, "");
})();
const OUT = path.join(ROOT, "reports", "logos_inquiry_ask_playwright_smoke_v1_latest.json");
const WAIT_MS = Math.max(120_000, parseInt(process.env.LOGOS_ASK_SMOKE_WAIT_MS || "300000", 10) || 300_000);

const QUESTION = "시편 23편 — lemma·경로 관점에서 연구 질문을 구체화해 달라";
const SCHOOL_QUESTION = "시편 23편 — 목자 비유와 학파별 해석";
const ASK_URL = `${BASE}/logos-research/ask?q=${encodeURIComponent(QUESTION)}&autorun=1`;
const SCHOOL_ASK_URL = `${BASE}/logos-research/ask?q=${encodeURIComponent(SCHOOL_QUESTION)}&autorun=1`;

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
  if (!pw) {
    console.error(JSON.stringify({ ok: false, error: "playwright_missing" }));
    process.exit(1);
  }

  const { chromium } = pw;
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(WAIT_MS);

  try {
    await page.goto(ASK_URL, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.waitForSelector(".lr-ask-input", { timeout: 60_000 });

    await page.waitForFunction(
      () => {
        const btn = document.querySelector(".lr-ask-composer .lr-btn-primary");
        const running = btn?.textContent?.includes("분석");
        const citationLock = document.querySelector(".lr-ask-citation-lock");
        const split = document.querySelector(".lr-ask-report-split");
        const s4Bodies = Array.from(document.querySelectorAll(".lr-ask-s4-section-body"));
        const s4Len = s4Bodies.length
          ? s4Bodies.map((el) => (el.textContent || "").trim()).join(" ").length
          : (document.querySelector(".lr-ask-s4-sections")?.textContent || "").trim().length;
        const graph = document.querySelector('[data-logos-ask-graph="1"]');
        const graphPhase = graph?.getAttribute("data-logos-ask-graph-phase") || "";
        const mindmap = document.querySelector('[data-logos-ask-graph="1"] [data-logos-path-mindmap="1"]');
        const svg = document.querySelector('[data-logos-ask-graph="1"] .lr-studio-mindmap-svg');
        const err = document.querySelector(".lr-ask-turn--error .lr-ask-bubble")?.textContent?.trim() || "";
        return (
          !running &&
          s4Len > 20 &&
          Boolean(citationLock) &&
          Boolean(split) &&
          Boolean(graph) &&
          (graphPhase === "done" || Boolean(mindmap) || Boolean(svg)) &&
          !err
        );
      },
      { timeout: WAIT_MS },
    );

    const snapshot = await page.evaluate(() => {
      const bubble = document.querySelector(".lr-ask-turn--assistant .lr-ask-bubble")?.textContent?.trim() || "";
      const pillCount = document.querySelectorAll(".lr-ask-section-pill").length;
      const sectionCount = document.querySelectorAll(".lr-ask-report-section").length;
      const s4SectionCount = document.querySelectorAll(".lr-ask-s4-section").length;
      const err = document.querySelector(".lr-ask-turn--error .lr-ask-bubble")?.textContent?.trim() || "";
      const s5final = document.body.textContent?.includes("final seal") || false;
      const s4Bodies = Array.from(document.querySelectorAll(".lr-ask-s4-section-body"));
      const s4Text = s4Bodies.length
        ? s4Bodies.map((el) => (el.textContent || "").trim()).join(" ")
        : (document.querySelector(".lr-ask-s4-sections")?.textContent || "").trim();
      const graphPanel = document.querySelector('[data-logos-ask-graph="1"]');
      const mindmap = document.querySelector('[data-logos-ask-graph="1"] [data-logos-path-mindmap="1"]');
      const graphSvg = document.querySelector('[data-logos-ask-graph="1"] .lr-studio-mindmap-svg');
      const graphPhase = graphPanel?.getAttribute("data-logos-ask-graph-phase") || "";
      const vizMode = graphPanel?.getAttribute("data-logos-ask-graph-viz") || "";
      const vizToggle = document.querySelectorAll(".lr-ask-graph-viz-btn").length;
      const citationLock = document.querySelector(".lr-ask-citation-lock") !== null;
      const split = document.querySelector(".lr-ask-report-split") !== null;
      const uiRev = document.querySelector("[data-logos-ask-ui-rev]")?.getAttribute("data-logos-ask-ui-rev") || "";
      const stubInS4 = /Path\s*envelope|orphan\s*veto|Gematria_Pin|GraphRAG\s*보조|primary_verse_refs\s*우선|stub\s*합선/i.test(s4Text);
      return {
        bubble_len: bubble.length,
        s4_len: s4Text.length,
        s4_section_count: s4SectionCount,
        s4_preview: s4Text.slice(0, 120),
        s4_stub_free: !stubInS4,
        section_pills: pillCount,
        section_blocks: sectionCount,
        s5_final: s5final,
        graph_panel: Boolean(graphPanel),
        graph_mindmap: Boolean(mindmap),
        graph_svg: Boolean(graphSvg),
        graph_phase: graphPhase,
        graph_viz_mode: vizMode,
        graph_viz_toggle_count: vizToggle,
        citation_lock: citationLock,
        report_split: split,
        ui_rev: uiRev,
        err,
      };
    });

    const ok =
      snapshot.s4_len > 20 &&
      snapshot.s4_section_count >= 1 &&
      snapshot.s4_stub_free !== false &&
      snapshot.citation_lock &&
      snapshot.graph_panel &&
      snapshot.report_split &&
      (snapshot.graph_mindmap || snapshot.graph_svg || snapshot.graph_phase === "done") &&
      !snapshot.err;

    // Done-Product P1 — school cards on Ring 0 (Psalm 23 + 학파 intent)
    await page.goto(SCHOOL_ASK_URL, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.waitForSelector(".lr-ask-input", { timeout: 60_000 });
    await page.waitForFunction(
      () => {
        const running = document.querySelector(".lr-ask-composer .lr-btn-primary")?.textContent?.includes("분석");
        const citationLock = document.querySelector(".lr-ask-citation-lock");
        const s4Bodies = Array.from(document.querySelectorAll(".lr-ask-s4-section-body"));
        const s4Len = s4Bodies.length
          ? s4Bodies.map((el) => (el.textContent || "").trim()).join(" ").length
          : (document.querySelector(".lr-ask-s4-sections")?.textContent || "").trim().length;
        const cards = document.querySelector('[data-lr-ask-school-cards="1"]');
        const rows = document.querySelectorAll(".lr-ask-school-cards--public .lr-ask-school-card");
        const schoolSource = cards?.getAttribute("data-lr-ask-school-source") || "";
        const err = document.querySelector(".lr-ask-turn--error .lr-ask-bubble")?.textContent?.trim() || "";
        return (
          !running &&
          s4Len > 20 &&
          Boolean(citationLock) &&
          Boolean(cards) &&
          rows.length >= 2 &&
          schoolSource === "live" &&
          !err
        );
      },
      { timeout: WAIT_MS },
    );

    const schoolSnapshot = await page.evaluate(() => {
      const cards = document.querySelector('[data-lr-ask-school-cards="1"]');
      const rows = document.querySelectorAll(".lr-ask-school-cards--public .lr-ask-school-card");
      const uiRev = document.querySelector("[data-logos-ask-ui-rev]")?.getAttribute("data-logos-ask-ui-rev") || "";
      return {
        school_cards: Boolean(cards),
        school_card_count: rows.length,
        school_source: cards?.getAttribute("data-lr-ask-school-source") || "",
        ui_rev: uiRev,
      };
    });

    const ring0Text = await page.evaluate(() => {
      const primary = document.querySelector(".lr-ask-report-primary");
      const lock = document.querySelector(".lr-ask-citation-lock");
      return `${lock?.textContent || ""}\n${primary?.textContent || ""}`;
    });
    const ring0Clean =
      !/\[NON_GATING\]|\[HYPO\]|Hub preset|citation lock anchors?:|research_only|send_gate/i.test(ring0Text);

    const productOk =
      schoolSnapshot.school_cards &&
      schoolSnapshot.school_card_count >= 2 &&
      schoolSnapshot.school_source === "live" &&
      schoolSnapshot.ui_rev === "20260703c" &&
      ring0Clean;

    const finalOk = ok && productOk;

    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(
      OUT,
      JSON.stringify(
        {
          schema: "logos_inquiry_ask_playwright_smoke_v1",
          version: "1.2.0",
          ok: finalOk,
          base: BASE,
          ask_url: ASK_URL,
          school_ask_url: SCHOOL_ASK_URL,
          wait_ms: WAIT_MS,
          snapshot,
          school_snapshot: schoolSnapshot,
          product_ok: productOk,
          ring0_clean: ring0Clean,
          generated_at_utc: new Date().toISOString(),
        },
        null,
        2,
      ),
    );
    console.log(
      JSON.stringify({
        ok: finalOk,
        base: BASE,
        out: OUT,
        product_ok: productOk,
        ring0_clean: ring0Clean,
        ...snapshot,
        ...schoolSnapshot,
      }),
    );
    if (!finalOk) process.exit(1);
  } catch (error) {
    console.error(JSON.stringify({ ok: false, base: BASE, wait_ms: WAIT_MS, error: String(error) }));
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
