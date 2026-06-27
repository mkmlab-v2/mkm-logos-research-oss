#!/usr/bin/env node
/** Smoke: logos-research studio API routes (dev: `npm run dev:studio` on 3020). */
const base = process.env.LOGOS_STUDIO_SMOKE_BASE || "http://127.0.0.1:3020";

const MINDMAP_NEEDLES = ["data-logos-path-mindmap", "경로 마인드맵", "lr-studio-mindmap"];

async function assertMindmapBundles(studioBase) {
  const studioUrl = `${studioBase}/logos-research/studio?q=job_job_suffering_reason&demo=1`;
  const studioPage = await fetch(studioUrl);
  if (!studioPage.ok) throw new Error(`mindmap_studio_http_${studioPage.status}`);
  const html = await studioPage.text();

  const chunkSet = new Set();
  for (const m of html.matchAll(/\/_next\/static\/chunks\/[^"']+\.js/g)) {
    chunkSet.add(m[0]);
  }
  const chunks = [...chunkSet];

  const hitChunks = [];
  for (const rel of chunks.slice(0, 24)) {
    try {
      const chunkRes = await fetch(`${studioBase}${rel}`);
      if (!chunkRes.ok) continue;
      const body = await chunkRes.text();
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
  const presets = await fetch(`${base}/api/logos-research/presets`);
  if (!presets.ok) throw new Error(`presets_http_${presets.status}`);
  const presetsBody = await presets.json();
  if (!presetsBody.ok || !Array.isArray(presetsBody.presets) || presetsBody.presets.length < 50) {
    throw new Error(`presets_body_invalid_count_${presetsBody.presets?.length ?? 0}`);
  }
  const bigsetIds = presetsBody.presets
    .map((p) => p.id)
    .filter((id) => typeof id === "string" && id.startsWith("bigset_topic_"));
  if (bigsetIds.length < 5) throw new Error("bigset_presets_missing");

  const nephilimQuery = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: "네피림이 뭐야?" }),
  });
  if (!nephilimQuery.ok) throw new Error(`nephilim_query_http_${nephilimQuery.status}`);
  const nephilimBody = await nephilimQuery.json();
  if (!nephilimBody.ok || nephilimBody.result?.preset_id !== "bigset_topic_nephilim") {
    throw new Error(`nephilim_query_mismatch_${nephilimBody.result?.preset_id ?? "none"}`);
  }

  const embeddingQuery = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: "타락한 천사가 인간 여성과 결혼했다는 고대 전통",
    }),
  });
  if (!embeddingQuery.ok) throw new Error(`embedding_query_http_${embeddingQuery.status}`);
  const embeddingBody = await embeddingQuery.json();
  const embPreset = embeddingBody.result?.preset_id;
  if (!embeddingBody.ok || !String(embPreset || "").startsWith("bigset_topic_")) {
    throw new Error(`embedding_query_mismatch_${embPreset ?? "none"}`);
  }

  const manifest = await fetch(`${base}/logos-research/manifest.webmanifest`);
  if (!manifest.ok) throw new Error(`manifest_http_${manifest.status}`);
  const manifestBody = await manifest.json();
  if (!manifestBody.start_url?.includes("/logos-research/studio")) {
    throw new Error("manifest_start_url_invalid");
  }

  const query = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset_id: "job_job_suffering_reason" }),
  });
  if (!query.ok) throw new Error(`query_http_${query.status}`);
  const queryBody = await query.json();
  if (!queryBody.ok || !queryBody.result?.preset_id) throw new Error("query_body_invalid");

  const highlightCount = (queryBody.result.highlight_node_ids || []).length;
  if (highlightCount < 1) throw new Error("highlight_node_ids_empty");
  if (!queryBody.result.subgraph?.graph_slice_url) throw new Error("subgraph_meta_missing");
  if ((queryBody.result.path?.node_ids || []).length < 1) {
    throw new Error("path_node_ids_empty");
  }

  const spineIds = queryBody.result.path?.reasoning_path_v1?.node_ids || [];
  if (spineIds.length < 2) throw new Error("reasoning_spine_short");

  const graphragQuery = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: "소망과 인내 시편 연결 경로" }),
  });
  if (!graphragQuery.ok) throw new Error(`graphrag_query_http_${graphragQuery.status}`);
  const graphragBody = await graphragQuery.json();
  const graphragMode = graphragBody.result?.query_mode || "";
  const graphragRefs = (graphragBody.result?.path?.verse_refs || []).length;
  if (!graphragBody.ok || !String(graphragMode).includes("graphrag")) {
    throw new Error(`graphrag_mode_missing_${graphragMode}`);
  }
  if (graphragRefs < 3) throw new Error("graphrag_verse_refs_short");

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

  const studioPage = await fetch(`${base}/logos-research/studio`);
  if (!studioPage.ok) throw new Error(`studio_html_${studioPage.status}`);
  const studioHtml = await studioPage.text();
  if (
    !studioHtml.includes("data-logos-studio-shell") &&
    !studioHtml.includes("logos-research-page") &&
    !studioHtml.includes("lr-studio")
  ) {
    throw new Error("studio_shell_missing");
  }

  const mindmapProbe = await assertMindmapBundles(base);

  const slice = await fetch(`${base}${queryBody.result.subgraph.graph_slice_url}`);
  if (!slice.ok) throw new Error(`graph_slice_http_${slice.status}`);
  const sliceBody = await slice.json();
  if (!Array.isArray(sliceBody.nodes) || sliceBody.nodes.length < 10) {
    throw new Error("graph_slice_nodes_invalid");
  }

  const sidecar = await fetch(`${base}/data/logos_studio/bigset_conflict_sidecar_v1.json`);
  if (!sidecar.ok) throw new Error(`sidecar_http_${sidecar.status}`);
  const sidecarBody = await sidecar.json();
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
      conflict_match_mode: nephilimConflict.match_mode,
      conflict_group_count: nephilimConflict.group_count,
      synthesis_mode: synthMode,
      nephilim_answer_len: answerLen,
      sidecar_groups: sidecarBody.groups.length,
      sidecar_pending: sidecarBody.observability?.human_review_pending_count ?? null,
      ...mindmapProbe,
    }),
  );
}

main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: String(error.message || error) }));
  process.exitCode = 1;
});
