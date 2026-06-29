#!/usr/bin/env node
/** Smoke: logos-research studio API routes (dev: `npm run dev:studio` on 3020).
 *  Prod (PowerShell): $env:LOGOS_STUDIO_SMOKE_BASE='https://logos.jema-ai.com'; npm run smoke:logos-studio
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const base = process.env.LOGOS_STUDIO_SMOKE_BASE || "http://127.0.0.1:3020";
const WORKSPACE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const ALLOWLIST_PATH = path.join(
  WORKSPACE_ROOT,
  "tests/fixtures/logos_studio_b2b_demo_preset_allowlist_v1.json",
);
const SMOKE_UA = "MKM-LogosStudioSmoke/1.0";
const ONBOARDING_NEEDLES = ["lr-studio-onboarding", "LogosStudioOnboarding"];

const MINDMAP_NEEDLES = ["data-logos-path-mindmap", "경로 마인드맵", "lr-studio-mindmap"];

function gateFor(spec, presetId, key) {
  const defaults = {
    min_answer_chars: Number(spec.min_answer_chars ?? 80),
    min_verse_refs: Number(spec.min_verse_refs ?? 1),
    min_highlight_nodes: Number(spec.min_highlight_nodes ?? 1),
  };
  const override = spec.preset_gates?.[presetId] ?? {};
  if (key in override) return Number(override[key]);
  return defaults[key];
}

const SMOKE_HEADERS = {
  "User-Agent": SMOKE_UA,
  Accept: "application/json",
};

async function getJson(url) {
  const res = await fetch(url, { headers: SMOKE_HEADERS });
  const body = await res.json().catch(() => ({}));
  return { res, body };
}

async function getText(url) {
  const res = await fetch(url, { headers: { "User-Agent": SMOKE_UA } });
  return { res, text: await res.text() };
}

async function postJson(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...SMOKE_HEADERS,
    },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  return { res, body };
}

async function assertChunkNeedles(studioBase, needles, label) {
  const studioPage = await getText(`${studioBase}/logos-research/studio`);
  if (!studioPage.res.ok) throw new Error(`${label}_studio_http_${studioPage.res.status}`);
  const html = studioPage.text;
  const chunkSet = new Set();
  for (const m of html.matchAll(/\/_next\/static\/chunks\/[^"']+\.js/g)) {
    chunkSet.add(m[0]);
  }
  const hitChunks = [];
  for (const rel of [...chunkSet].slice(0, 28)) {
    try {
      const chunkRes = await getText(`${studioBase}${rel}`);
      if (!chunkRes.res.ok) continue;
      const body = chunkRes.text;
      if (needles.some((n) => body.includes(n))) {
        hitChunks.push(rel.split("/").pop());
      }
    } catch {
      /* skip */
    }
  }
  const htmlMarker = needles.some((n) => html.includes(n));
  if (hitChunks.length < 1 && !htmlMarker) {
    throw new Error(`${label}_bundle_missing`);
  }
  return { chunk_hits: hitChunks.length, html_marker: htmlMarker, sample_chunks: hitChunks.slice(0, 3) };
}

async function assertB2bDemoPresetAllowlist() {
  const spec = JSON.parse(readFileSync(ALLOWLIST_PATH, "utf8"));
  const presetIds = spec.preset_ids || [];
  if (presetIds.length < 1) throw new Error("allowlist_empty");
  const rows = [];
  for (const presetId of presetIds) {
    const { res, body } = await postJson(`${base}/api/logos-research/query`, { preset_id: presetId });
    if (!res.ok) throw new Error(`allowlist_${presetId}_http_${res.status}`);
    if (!body.ok) throw new Error(`allowlist_${presetId}_api_not_ok`);
    const result = body.result || {};
    const answerLen = String(result.answer || "").length;
    const verseRefs = (result.path?.verse_refs || []).length;
    const highlights = (result.highlight_node_ids || []).length;
    if (answerLen < gateFor(spec, presetId, "min_answer_chars")) {
      throw new Error(`allowlist_${presetId}_answer_short_${answerLen}`);
    }
    if (verseRefs < gateFor(spec, presetId, "min_verse_refs")) {
      throw new Error(`allowlist_${presetId}_verse_refs_${verseRefs}`);
    }
    if (highlights < gateFor(spec, presetId, "min_highlight_nodes")) {
      throw new Error(`allowlist_${presetId}_highlight_${highlights}`);
    }
    rows.push({ preset_id: presetId, answer_len: answerLen, verse_refs: verseRefs, highlights });
  }
  return { allowlist_count: rows.length, allowlist_rows: rows };
}

async function assertLandingIa() {
  const landing = await getText(`${base}/logos-research`);
  if (!landing.res.ok) throw new Error(`landing_http_${landing.res.status}`);
  const html = landing.text;
  for (const id of ["value", "pilot", "architecture", "lead"]) {
    if (!html.includes(`id="${id}"`)) throw new Error(`landing_section_missing_${id}`);
  }
  if (!html.includes("LogosResearchLandingLeadForm") && !html.includes("lr-landing-lead")) {
    throw new Error("landing_lead_form_missing");
  }
  return { landing_sections: ["value", "pilot", "architecture", "lead"] };
}

async function assertLeadApi() {
  const bad = await postJson(`${base}/api/logos-research/lead`, { email: "not-an-email" });
  if (bad.res.status !== 400 || bad.body.ok !== false) {
    throw new Error(`lead_invalid_email_gate_${bad.res.status}`);
  }
  const ok = await postJson(`${base}/api/logos-research/lead`, {
    email: `smoke+${Date.now()}@example.com`,
    organization: "smoke-test",
    note: "automated smoke — safe to ignore",
    source: "logos-research-smoke-v1",
    tier: "pilot",
  });
  if (!ok.res.ok || !ok.body.ok || !ok.body.lead_id) {
    throw new Error(`lead_submit_failed_${ok.res.status}`);
  }
  return { lead_id: ok.body.lead_id };
}

async function assertMindmapBundles(studioBase) {
  const studioUrl = `${studioBase}/logos-research/studio?q=job_job_suffering_reason&demo=1`;
  const studioPage = await getText(studioUrl);
  if (!studioPage.res.ok) throw new Error(`mindmap_studio_http_${studioPage.res.status}`);
  const html = studioPage.text;

  const chunkSet = new Set();
  for (const m of html.matchAll(/\/_next\/static\/chunks\/[^"']+\.js/g)) {
    chunkSet.add(m[0]);
  }
  const chunks = [...chunkSet];

  const hitChunks = [];
  for (const rel of chunks.slice(0, 24)) {
    try {
      const chunkRes = await getText(`${studioBase}${rel}`);
      if (!chunkRes.res.ok) continue;
      const body = chunkRes.text;
      if (MINDMAP_NEEDLES.some((n) => body.includes(n))) {
        hitChunks.push(rel.split("/").pop());
      }
    } catch {
      /* skip unreachable chunk */
    }
  }

  const htmlMarker =
    MINDMAP_NEEDLES.some((n) => html.includes(n)) ||
    html.includes("lr-studio-tab-mindmap");

  if (hitChunks.length < 1 && !htmlMarker) {
    throw new Error("mindmap_bundle_missing");
  }

  return {
    mindmap_chunk_hits: hitChunks.length,
    mindmap_html_marker: htmlMarker,
    mindmap_sample_chunks: hitChunks.slice(0, 3),
  };
}

async function main() {
  const { res: presets, body: presetsBody } = await getJson(`${base}/api/logos-research/presets`);
  if (!presets.ok) throw new Error(`presets_http_${presets.status}`);
  if (!presetsBody.ok || !Array.isArray(presetsBody.presets) || presetsBody.presets.length < 50) {
    throw new Error(`presets_body_invalid_count_${presetsBody.presets?.length ?? 0}`);
  }
  const bigsetIds = presetsBody.presets
    .map((p) => p.id)
    .filter((id) => typeof id === "string" && id.startsWith("bigset_topic_"));
  if (bigsetIds.length < 5) throw new Error("bigset_presets_missing");

  const { res: nephilimQuery, body: nephilimBody } = await postJson(
    `${base}/api/logos-research/query`,
    { query: "네피림이 뭐야?" },
  );
  if (!nephilimQuery.ok) throw new Error(`nephilim_query_http_${nephilimQuery.status}`);
  if (!nephilimBody.ok || nephilimBody.result?.preset_id !== "bigset_topic_nephilim") {
    throw new Error(`nephilim_query_mismatch_${nephilimBody.result?.preset_id ?? "none"}`);
  }

  const { res: mismatchQuery, body: mismatchBody } = await postJson(
    `${base}/api/logos-research/query`,
    {
      preset_id: "job_job_suffering_reason",
      query: "네피림",
    },
  );
  if (!mismatchQuery.ok) throw new Error(`mismatch_query_http_${mismatchQuery.status}`);
  if (!mismatchBody.ok || mismatchBody.result?.preset_id !== "bigset_topic_nephilim") {
    throw new Error(
      `mismatch_auto_route_failed_${mismatchBody.result?.preset_id ?? "none"}_${mismatchBody.preset_guard?.action ?? "no_guard"}`,
    );
  }
  if (mismatchBody.preset_guard?.action !== "auto_route") {
    throw new Error(`mismatch_guard_action_${mismatchBody.preset_guard?.action ?? "none"}`);
  }

  const { res: embeddingQuery, body: embeddingBody } = await postJson(
    `${base}/api/logos-research/query`,
    {
      query: "타락한 천사가 인간 여성과 결혼했다는 고대 전통",
    },
  );
  if (!embeddingQuery.ok) throw new Error(`embedding_query_http_${embeddingQuery.status}`);
  const embPreset = embeddingBody.result?.preset_id;
  if (!embeddingBody.ok || !String(embPreset || "").startsWith("bigset_topic_")) {
    throw new Error(`embedding_query_mismatch_${embPreset ?? "none"}`);
  }

  const { res: manifest, body: manifestBody } = await getJson(`${base}/logos-research/manifest.webmanifest`);
  if (!manifest.ok) throw new Error(`manifest_http_${manifest.status}`);
  if (!manifestBody.start_url?.includes("/logos-research/studio")) {
    throw new Error("manifest_start_url_invalid");
  }

  const { res: query, body: queryBody } = await postJson(`${base}/api/logos-research/query`, {
    preset_id: "job_job_suffering_reason",
  });
  if (!query.ok) throw new Error(`query_http_${query.status}`);
  if (!queryBody.ok || !queryBody.result?.preset_id) throw new Error("query_body_invalid");

  const highlightCount = (queryBody.result.highlight_node_ids || []).length;
  if (highlightCount < 1) throw new Error("highlight_node_ids_empty");
  if (!queryBody.result.subgraph?.graph_slice_url) throw new Error("subgraph_meta_missing");
  if ((queryBody.result.path?.node_ids || []).length < 1) {
    throw new Error("path_node_ids_empty");
  }

  const spineIds = queryBody.result.path?.reasoning_path_v1?.node_ids || [];
  if (spineIds.length < 2) throw new Error("reasoning_spine_short");

  const { res: graphragQuery, body: graphragBody } = await postJson(
    `${base}/api/logos-research/query`,
    { query: "소망과 인내 시편 연결 경로" },
  );
  if (!graphragQuery.ok) throw new Error(`graphrag_query_http_${graphragQuery.status}`);
  const graphragMode = graphragBody.result?.query_mode || "";
  const graphragRefs = (graphragBody.result?.path?.verse_refs || []).length;
  if (!graphragBody.ok || !String(graphragMode).includes("graphrag")) {
    throw new Error(`graphrag_mode_missing_${graphragMode}`);
  }
  if (graphragRefs < 3) throw new Error("graphrag_verse_refs_short");
  const lemmaBridgeMode = graphragBody.result?.query_mode || "";
  const lemmaNeighbors = graphragBody.result?.lemma_bridge_meta?.neighbor_count || 0;
  if (!String(lemmaBridgeMode).includes("lemma_bridge")) {
    throw new Error(`lemma_bridge_mode_missing_${lemmaBridgeMode}`);
  }
  if (lemmaNeighbors < 1) throw new Error("lemma_bridge_neighbors_empty");

  const nephilimConflict = nephilimBody.result?.conflict_context;
  if (!nephilimConflict?.ok || (nephilimConflict.group_count || 0) < 1) {
    throw new Error("nephilim_conflict_context_missing");
  }
  const nephGids = (nephilimConflict.groups || []).map((g) => g.conflict_group_id);
  if (!nephGids.includes("MKM_CONCEPT_NEPHILIM")) {
    throw new Error(`nephilim_conflict_group_mismatch_${nephGids.join(",")}`);
  }
  const synthMode = nephilimBody.result?.synthesis_meta?.synthesis_mode || "";
  if (!String(nephilimBody.result?.query_mode || "").includes("synthesis")) {
    throw new Error(`nephilim_synthesis_missing_${nephilimBody.result?.query_mode ?? "none"}`);
  }
  if (!synthMode.includes("deterministic")) {
    throw new Error(`nephilim_synthesis_mode_${synthMode}`);
  }
  const answerLen = String(nephilimBody.result?.answer || "").length;
  if (answerLen < 200) throw new Error(`nephilim_answer_short_${answerLen}`);

  const studioPage = await getText(`${base}/logos-research/studio`);
  if (!studioPage.res.ok) throw new Error(`studio_html_${studioPage.res.status}`);
  const studioHtml = studioPage.text;
  const studioShellHtmlMarker =
    studioHtml.includes("data-logos-studio-route") ||
    studioHtml.includes("logos-research-studio-route") ||
    studioHtml.includes("data-logos-studio-shell") ||
    studioHtml.includes("logos-research-page") ||
    studioHtml.includes("lr-studio");
  const studioShellProbe = studioShellHtmlMarker
    ? { studio_shell: "html", studio_shell_html_marker: true }
    : await assertChunkNeedles(
        base,
        ["data-logos-studio-shell", "logos-research-page", "lr-studio"],
        "studio_shell",
      );

  const mindmapProbe = await assertMindmapBundles(base);
  const onboardingProbe = await assertChunkNeedles(base, ONBOARDING_NEEDLES, "onboarding");
  const allowlistProbe = await assertB2bDemoPresetAllowlist();
  const landingProbe = await assertLandingIa();
  const leadProbe = await assertLeadApi();

  const { res: slice, body: sliceBody } = await getJson(`${base}${queryBody.result.subgraph.graph_slice_url}`);
  if (!slice.ok) throw new Error(`graph_slice_http_${slice.status}`);
  if (!Array.isArray(sliceBody.nodes) || sliceBody.nodes.length < 10) {
    throw new Error("graph_slice_nodes_invalid");
  }

  const { res: sidecar, body: sidecarBody } = await getJson(
    `${base}/data/logos_studio/bigset_conflict_sidecar_v1.json`,
  );
  if (!sidecar.ok) throw new Error(`sidecar_http_${sidecar.status}`);
  if (sidecarBody.schema !== "bigset_studio_conflict_sidecar_v1") {
    throw new Error("sidecar_schema_invalid");
  }
  if (!Array.isArray(sidecarBody.groups) || sidecarBody.groups.length < 1) {
    throw new Error("sidecar_groups_empty");
  }

  console.log(
    JSON.stringify({
      ok: true,
      preset_count: presetsBody.presets.length,
      bigset_preset_ids: bigsetIds,
      nephilim_match: nephilimBody.result?.preset_id,
      nephilim_router_match: nephilimBody.match,
      embedding_match: embeddingBody.result?.preset_id,
      embedding_router_match: embeddingBody.match,
      mobile_manifest: manifestBody.short_name,
      sample_preset: queryBody.result.preset_id,
      verse_refs: (queryBody.result.path?.verse_refs || []).length,
      highlight_node_ids: highlightCount,
      path_node_ids: (queryBody.result.path?.node_ids || []).length,
      spine_node_ids: spineIds.length,
      graph_nodes: sliceBody.nodes.length,
      graphrag_mode: graphragMode,
      graphrag_verse_refs: graphragRefs,
      lemma_bridge_neighbors: lemmaNeighbors,
      conflict_match_mode: nephilimConflict.match_mode,
      conflict_group_count: nephilimConflict.group_count,
      synthesis_mode: synthMode,
      nephilim_answer_len: answerLen,
      sidecar_groups: sidecarBody.groups.length,
      sidecar_pending: sidecarBody.observability?.human_review_pending_count ?? null,
      ...mindmapProbe,
      ...studioShellProbe,
      onboarding_chunk_hits: onboardingProbe.chunk_hits,
      onboarding_html_marker: onboardingProbe.html_marker,
      ...allowlistProbe,
      ...landingProbe,
      ...leadProbe,
    }),
  );
}

main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: String(error.message || error) }));
  process.exitCode = 1;
});
