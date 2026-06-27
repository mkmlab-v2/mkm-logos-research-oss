/**
 * Self-audit: why mindmap may feel below expectation (richness vs smoke gates).
 */
import { writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../../..");
const OUT = path.join(ROOT, "reports", "logos_mindmap_expectation_gap_audit_v1_latest.json");
const BASE = (process.env.LOGOS_STUDIO_SMOKE_BASE || "https://logos.jema-ai.com").replace(/\/$/, "");

async function loadPlaywright() {
  const candidates = [
    path.join(__dirname, "..", "node_modules", "playwright", "index.mjs"),
    path.join(__dirname, "..", "node_modules", "playwright", "index.js"),
    path.join(ROOT, "node_modules", "playwright", "index.mjs"),
    path.join(ROOT, "projects", "mkm", "mkm-life", "node_modules", "playwright", "index.mjs"),
    path.join(ROOT, "projects", "mkm-life", "node_modules", "playwright", "index.mjs"),
  ];
  for (const candidate of candidates) {
    try {
      return await import(pathToFileURL(candidate).href);
    } catch {
      // next
    }
  }
  throw new Error("playwright_not_installed");
}

async function auditMindmap(page, label) {
  await page.waitForSelector('[data-logos-path-mindmap="1"]', { timeout: 90000 });
  return page.evaluate((lbl) => {
    const panel = document.querySelector('[data-logos-path-mindmap="1"]');
    const svg = panel?.querySelector("svg");
    const circles = svg ? svg.querySelectorAll("circle").length : 0;
    const edges = svg ? svg.querySelectorAll(".lr-studio-mindmap-edge").length : 0;
    const labels = [...(svg?.querySelectorAll("text") || [])].map((t) => ({
      text: (t.textContent || "").trim(),
      fontSize: getComputedStyle(t).fontSize,
      truncated: (t.textContent || "").includes("…"),
    }));
    const stage = panel?.querySelector(".lr-studio-mindmap-stage");
    const stageBox = stage?.getBoundingClientRect();
    const titleEl = panel?.querySelector(".lr-studio-mindmap-title");
    const titleStyle = titleEl ? getComputedStyle(titleEl) : null;
    const heroCard = document.querySelector(".lr-hero-inline-demo-card");
    const storyboard = document.querySelector(".lr-hero-inline-demo-storyboard");
    return {
      label: lbl,
      node_circles: circles,
      edge_paths: edges,
      label_count: labels.length,
      truncated_labels: labels.filter((l) => l.truncated).length,
      labels_sample: labels.slice(0, 8),
      stage_px: stageBox ? { w: Math.round(stageBox.width), h: Math.round(stageBox.height) } : null,
      title_color: titleStyle?.color || null,
      title_text: titleEl?.textContent?.trim() || null,
      hero_card_overflow: heroCard ? heroCard.scrollHeight > heroCard.clientHeight + 2 : null,
      hero_card_px: heroCard
        ? { clientH: Math.round(heroCard.clientHeight), scrollH: Math.round(heroCard.scrollHeight) }
        : null,
      storyboard_present: !!storyboard,
      footnote: panel?.querySelector(".lr-studio-mindmap-foot")?.textContent?.trim() || null,
    };
  }, label);
}

async function main() {
  const pw = await loadPlaywright();
  const browser = await pw.chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const doc = {
    schema: "logos_mindmap_expectation_gap_audit_v1",
    base: BASE,
    audited_at_utc: new Date().toISOString(),
    checks: [],
    gaps: [],
  };

  await page.goto(`${BASE}/logos-research`, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.locator('[data-logos-graph-studio-inline="1"]').waitFor({ timeout: 60000 });
  doc.checks.push(await auditMindmap(page, "hero_landing"));

  await page.goto(
    `${BASE}/logos-research/studio?q=job_job_suffering_reason&autorun=1&demo=1`,
    { waitUntil: "domcontentloaded", timeout: 120000 },
  );
  await page.locator("#lr-studio-tab-mindmap").waitFor({ timeout: 60000 });
  doc.checks.push(await auditMindmap(page, "studio_mindmap"));

  await page.locator("#lr-studio-tab-auditor").click();
  await page.waitForTimeout(1200);
  doc.auditor = await page.evaluate(() => {
    const panel = document.querySelector(".lr-studio-graph-panel--auditor");
    const canvas = panel?.querySelector("canvas");
    const meshControls = document.querySelectorAll("[data-mesh-depth], .lr-studio-mesh").length;
    return {
      canvas_present: !!canvas,
      canvas_px: canvas
        ? { w: Math.round(canvas.getBoundingClientRect().width), h: Math.round(canvas.getBoundingClientRect().height) }
        : null,
      panel_text_snippet: (panel?.textContent || "").replace(/\s+/g, " ").trim().slice(0, 280),
      mesh_control_nodes: meshControls,
    };
  });

  const hero = doc.checks.find((c) => c.label === "hero_landing");
  const studio = doc.checks.find((c) => c.label === "studio_mindmap");

  if (hero?.node_circles <= 10) {
    doc.gaps.push({
      id: "sparse_graph",
      severity: "high",
      fact: `hero mindmap renders only ${hero.node_circles} nodes while studio API reports graph_nodes≈320`,
      why_it_feels_weak: "마인드맵이 '망'이 아니라 path 요약 다이어그램에 가깝다",
    });
  }
  if (hero?.stage_px?.h <= 230) {
    doc.gaps.push({
      id: "hero_cramped",
      severity: "high",
      fact: `hero stage height ${hero.stage_px.h}px (fixed 220) inside scroll card max-height 30rem`,
      why_it_feels_weak: "라벨·노드 밀도가 높을 때 히어로에서 답답하고 잘림",
    });
  }
  if (hero?.truncated_labels > 0 || studio?.truncated_labels > 0) {
    doc.gaps.push({
      id: "label_truncation",
      severity: "med",
      fact: `truncated labels hero=${hero?.truncated_labels} studio=${studio?.truncated_labels}`,
      why_it_feels_weak: "구절·질의가 … 로 잘려 정보 밀도 대비 가독성 저하",
    });
  }
  if (hero?.hero_card_overflow) {
    doc.gaps.push({
      id: "hero_scroll_clutter",
      severity: "med",
      fact: `hero card scrolls (${hero.hero_card_px?.scrollH}px > ${hero.hero_card_px?.clientH}px)`,
      why_it_feels_weak: "스토리보드+마인드맵이 한 카드에 겹쳐 '완성 UI'보다 데모 패널처럼 보임",
    });
  }
  doc.gaps.push({
    id: "smoke_gate_too_thin",
    severity: "high",
    fact: "Playwright smoke only asserts bbox>=80px + visible marker",
    why_it_feels_weak: "배포·통과와 체감 품질이 분리됨 — 색 수정만으로는 구조 한계가 안 보임",
  });
  doc.gaps.push({
    id: "preset_layout_unwired",
    severity: "high",
    fact: "layoutPathMindmapRadial accepts presetId but void opts?.presetId (generic radial only)",
    why_it_feels_weak: "Figma/Job spine 고정 좌표·일러스트 없음 — '디자인된 마인드맵' 기대와 불일치",
  });
  doc.gaps.push({
    id: "dual_viz_split",
    severity: "med",
    fact: "320-node force graph is auditor tab only; default tab is ~10-node path mindmap",
    why_it_feels_weak: "사용자가 기대하는 infinite mesh/코퍼스 망과 기본 탭 경험이 다름",
  });

  doc.smoke_passes = {
    playwright: "bbox>=80 only",
    studio_api: "mindmap_chunk_hits>=2",
    probe: "string in JS bundle",
  };

  mkdirSync(path.dirname(OUT), { recursive: true });
  writeFileSync(OUT, `${JSON.stringify(doc, null, 2)}\n`);
  console.log(JSON.stringify({ ok: true, gaps: doc.gaps.length, out: OUT }));
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
