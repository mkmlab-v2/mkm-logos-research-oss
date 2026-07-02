/**
 * Live dev hot-reload verify — /logos-research/ask graph sidecar (Playwright).
 * Prereq: npm run dev:logos (127.0.0.1:3010)
 *
 *   npm run verify:logos-ask-graph-live
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
const OUT = path.join(ROOT, "reports", "logos_ask_graph_live_verify_v1_latest.json");
const WAIT_MS = Math.max(120_000, parseInt(process.env.LOGOS_ASK_SMOKE_WAIT_MS || "300000", 10) || 300_000);

const QUESTION = "시편 23편 — lemma·경로 관점에서 연구 질문을 구체화해 달라";
const ASK_URL = `${BASE}/logos-research/ask?q=${encodeURIComponent(QUESTION)}&autorun=1`;

const HYDRATION_RE = /hydration|did not match|Text content does/i;
const STRICT_HYDRATION = process.env.MKM_STRICT_HYDRATION === "1";

const READ_UI_STATE = `() => {
  const bubble = document.querySelector(".lr-ask-turn--assistant .lr-ask-bubble")?.textContent?.trim() || "";
  const running = document.querySelector(".lr-ask-composer .lr-btn-primary")?.textContent?.includes("분석");
  const citationLock = document.querySelector(".lr-ask-citation-lock");
  const citationGate = document.querySelector(".lr-ask-citation-lock-gate");
  const citationChips = document.querySelectorAll(".lr-ask-citation-lock-ref-chip").length;
  const split = document.querySelector(".lr-ask-report-split");
  const graph = document.querySelector('[data-logos-ask-graph="1"]');
  const mindmap = document.querySelector('[data-logos-ask-graph="1"] [data-logos-path-mindmap="1"]');
  const svg = document.querySelector('[data-logos-ask-graph="1"] .lr-studio-mindmap-svg');
  const narrative = (() => {
    const bodies = Array.from(document.querySelectorAll(".lr-ask-s4-section-body"));
    if (bodies.length) {
      return bodies.map((el) => (el.textContent || "").trim()).join(" ");
    }
    return (document.querySelector(".lr-ask-s4-sections")?.textContent || "").trim();
  })();
  const err = document.querySelector(".lr-ask-turn--error .lr-ask-bubble")?.textContent?.trim() || "";
  return {
    running: Boolean(running),
    bubble_len: bubble.length,
    narrative_len: narrative.length,
    citation_lock: Boolean(citationLock),
    citation_lock_gate: Boolean(citationGate),
    citation_lock_chips: citationChips,
    report_split: Boolean(split),
    graph_panel: Boolean(graph),
    graph_mindmap: Boolean(mindmap),
    graph_svg: Boolean(svg),
    graph_phase: graph?.getAttribute("data-logos-ask-graph-phase") || "",
    graph_viz: graph?.getAttribute("data-logos-ask-graph-viz") || "",
    viz_toggle_count: document.querySelectorAll(".lr-ask-graph-viz-btn").length,
    report_expand_btn: Boolean(document.querySelector(".lr-ask-expand-btn")),
    err,
  };
}`;

async function loadPlaywright() {
  const candidates = [
    path.join(NO1K, "node_modules", "playwright", "index.mjs"),
    path.join(NO1K, "node_modules", "playwright", "index.js"),
  ];
  for (const candidate of candidates) {
    try {
      return await import(pathToFileURL(candidate).href);
    } catch {
      // continue
    }
  }
  return import("playwright").catch(() => null);
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
  const consoleViolations = [];
  page.on("console", (msg) => {
    const type = msg.type();
    const text = msg.text();
    if ((type === "error" || type === "warning") && HYDRATION_RE.test(text)) {
      consoleViolations.push({ type, text: text.slice(0, 500) });
    }
  });
  page.on("pageerror", (err) => {
    consoleViolations.push({ type: "pageerror", text: String(err).slice(0, 500) });
  });
  page.setDefaultTimeout(WAIT_MS);

  try {
    await page.goto(ASK_URL, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.waitForSelector(".lr-ask-input", { timeout: 60_000 });

    await page.waitForFunction(
      () => {
        const citationLock = document.querySelector(".lr-ask-citation-lock");
        const err = document.querySelector(".lr-ask-turn--error .lr-ask-bubble")?.textContent?.trim() || "";
        return Boolean(citationLock) && !err;
      },
      { timeout: WAIT_MS },
    );

    const mid = await page.evaluate(new Function(`return (${READ_UI_STATE})();`));

    await page.waitForFunction(
      () => {
        const running = document.querySelector(".lr-ask-composer .lr-btn-primary")?.textContent?.includes("분석");
        const graph = document.querySelector('[data-logos-ask-graph="1"]');
        const mindmap = document.querySelector('[data-logos-ask-graph="1"] [data-logos-path-mindmap="1"]');
        const svg = document.querySelector('[data-logos-ask-graph="1"] .lr-studio-mindmap-svg');
        const graphPhase = graph?.getAttribute("data-logos-ask-graph-phase") || "";
        const s4Bodies = Array.from(document.querySelectorAll(".lr-ask-s4-section-body"));
        const s4Len = s4Bodies.length
          ? s4Bodies.map((el) => (el.textContent || "").trim()).join(" ").length
          : (document.querySelector(".lr-ask-s4-sections")?.textContent || "").trim().length;
        const err = document.querySelector(".lr-ask-turn--error .lr-ask-bubble")?.textContent?.trim() || "";
        return (
          !running &&
          Boolean(graph) &&
          (graphPhase === "done" || Boolean(mindmap) || Boolean(svg)) &&
          s4Len > 20 &&
          !err
        );
      },
      { timeout: WAIT_MS },
    );

    const final = await page.evaluate(new Function(`return (${READ_UI_STATE})();`));

    const ok =
      final.citation_lock &&
      final.citation_lock_gate &&
      final.citation_lock_chips > 0 &&
      final.report_split &&
      final.graph_panel &&
      (final.graph_mindmap || final.graph_svg || final.graph_phase === "done") &&
      final.narrative_len > 20 &&
      !final.err &&
      !(STRICT_HYDRATION && consoleViolations.length);

    const payload = {
      schema: "logos_ask_graph_live_verify_v1",
      ok,
      base: BASE,
      ask_url: ASK_URL,
      wait_ms: WAIT_MS,
      console_violations: consoleViolations,
      strict_hydration: STRICT_HYDRATION,
      mid,
      final,
      generated_at_utc: new Date().toISOString(),
    };
    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(OUT, JSON.stringify(payload, null, 2));
    console.log(JSON.stringify({ ok, out: OUT, console_violations: consoleViolations.length, ...final }));
    if (!ok) process.exit(1);
  } catch (error) {
    let partial = null;
    try {
      partial = await page.evaluate(new Function(`return (${READ_UI_STATE})();`));
    } catch {
      // ignore
    }
    const fail = {
      schema: "logos_ask_graph_live_verify_v1",
      ok: false,
      base: BASE,
      wait_ms: WAIT_MS,
      partial,
      error: String(error),
      generated_at_utc: new Date().toISOString(),
    };
    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(OUT, JSON.stringify(fail, null, 2));
    console.error(JSON.stringify(fail));
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
