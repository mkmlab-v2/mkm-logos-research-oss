import { readFile } from "node:fs/promises";

import path from "node:path";



import {

  resolveHighlightNodeIds,

  type LogosReasoningPathV1,

  type LogosRouterPathV1,

} from "./logosResearchHighlightV1";

import {
  resolvePresetFromEmbeddingIndex,
  resolvePresetFromLexicalIndex,
  type LogosStudioEmbeddingIndex,
  type LogosStudioLexicalIndex,
} from "./logosStudioSemanticRouterV1";
import {
  encodeLogosStudioQueryEmbedding,
  logosStudioEmbeddingRouterEnabled,
} from "./logosStudioEmbeddingBridgeV1";
import {
  encodeLogosStudioQueryGraphrag,
  logosStudioGraphragRouterEnabled,
  type GraphragEncodeResult,
} from "./logosStudioGraphragBridgeV1";
import {
  logosStudioConflictRetrievalEnabled,
  retrieveLogosStudioConflictContext,
  type ConflictContextResult,
} from "./logosStudioConflictBridgeV1";
import {
  logosStudioDynamicSynthesisEnabled,
  synthesizeLogosStudioDynamicAnswer,
  type SynthesisResult,
} from "./logosStudioSynthesisBridgeV1";



export const LOGOS_STUDIO_DATA_DIR = path.join(process.cwd(), "public", "data", "logos_studio");

export const LOGOS_STUDIO_GRAPH_SLICE_URL = "/data/logos_studio/graph_slice_v1.json";



export type LogosStudioPreset = {

  id: string;

  prompt_ko: string;

  answer_ko?: string;

  answer_ko_product?: string;

  highlight_node_ids?: string[];

  keywords?: string[];

  bigset_conflict_group_id?: string;

  reasoning_path_v1?: LogosReasoningPathV1;

  router_path_v1?: LogosRouterPathV1;

};



export type LogosStudioPresetsDoc = {

  presets: LogosStudioPreset[];

  disclaimer?: Record<string, unknown>;

};



export type LogosStudioRouterPath = LogosRouterPathV1;



export type LogosStudioRouterSidecar = {

  presets: Record<

    string,

    {

      router_summary?: { bridges_matched?: number; paths?: number; verse_ids?: number };

      router_path_v1?: LogosStudioRouterPath;

    }

  >;

};



export type LogosStudioInsightCard = {
  preset_id: string;
  slot: string;
  slot_label_ko?: string;
  one_liner_ko?: string;
  verse_anchors?: string[];
  gap_ko?: string;
  governance?: string;
};

export type LogosStudioPresetTaxonomy = {
  insight_cards?: Record<string, LogosStudioInsightCard>;
};

let presetsCache: LogosStudioPresetsDoc | null = null;

let routerCache: LogosStudioRouterSidecar | null = null;

let taxonomyCache: LogosStudioPresetTaxonomy | null = null;

let lexicalIndexCache: LogosStudioLexicalIndex | null = null;

let embeddingIndexCache: LogosStudioEmbeddingIndex | null = null;



async function readJson<T>(fileName: string): Promise<T> {

  const raw = await readFile(path.join(LOGOS_STUDIO_DATA_DIR, fileName), "utf8");

  return JSON.parse(raw) as T;

}



export async function loadLogosStudioPresets(): Promise<LogosStudioPresetsDoc> {

  if (!presetsCache) {

    presetsCache = await readJson<LogosStudioPresetsDoc>("qa_presets_v1.json");

  }

  return presetsCache;

}



export async function loadLogosStudioRouter(): Promise<LogosStudioRouterSidecar> {

  if (!routerCache) {

    routerCache = await readJson<LogosStudioRouterSidecar>("qa_router_sidecar_v1.json");

  }

  return routerCache;

}



export async function loadLogosStudioTaxonomy(): Promise<LogosStudioPresetTaxonomy> {

  if (!taxonomyCache) {

    try {

      taxonomyCache = await readJson<LogosStudioPresetTaxonomy>("preset_taxonomy_v1.json");

    } catch {

      taxonomyCache = { insight_cards: {} };

    }

  }

  return taxonomyCache;

}



export function mergePresetRouterPath(

  preset: LogosStudioPreset,

  router?: LogosStudioRouterSidecar["presets"][string],

): LogosRouterPathV1 | undefined {

  const fromSidecar = router?.router_path_v1;

  const fromPreset = preset.router_path_v1;

  if (!fromSidecar && !fromPreset) return undefined;

  return {

    ...fromPreset,

    ...fromSidecar,

    reasoning_path_v1:

      fromSidecar?.reasoning_path_v1 ??

      fromPreset?.reasoning_path_v1 ??

      preset.reasoning_path_v1,

  };

}



export function normalizeQueryText(value: string): string {

  return value.trim().toLowerCase().replace(/\s+/g, " ");

}



export async function loadLogosStudioLexicalIndex(): Promise<LogosStudioLexicalIndex> {

  if (!lexicalIndexCache) {

    try {

      lexicalIndexCache = await readJson<LogosStudioLexicalIndex>(
        "semantic_router_lexical_index_v1.json",
      );

    } catch {

      lexicalIndexCache = { inverted_index: [] };

    }

  }

  return lexicalIndexCache;

}



export async function loadLogosStudioEmbeddingIndex(): Promise<LogosStudioEmbeddingIndex> {

  if (!embeddingIndexCache) {

    try {

      embeddingIndexCache = await readJson<LogosStudioEmbeddingIndex>(
        "semantic_router_embedding_index_v1.json",
      );

    } catch {

      embeddingIndexCache = { vectors: [] };

    }

  }

  return embeddingIndexCache;

}



export function resolvePresetId(

  presets: LogosStudioPreset[],

  opts: { preset_id?: string; query?: string },

  lexicalIndex?: LogosStudioLexicalIndex | null,

): { preset_id: string | null; match: "id" | "text" | "lexical" | "embedding" | "none" } {

  if (opts.preset_id) {

    const byId = presets.find((p) => p.id === opts.preset_id);

    if (byId) return { preset_id: byId.id, match: "id" };

  }

  const q = normalizeQueryText(opts.query || "");

  if (!q) return { preset_id: null, match: "none" };



  const exact = presets.find((p) => normalizeQueryText(p.prompt_ko) === q);

  if (exact) return { preset_id: exact.id, match: "text" };



  let best: { id: string; score: number } | null = null;

  for (const preset of presets) {

    const prompt = normalizeQueryText(preset.prompt_ko);

    let score = 0;

    if (prompt.includes(q) || q.includes(prompt.slice(0, Math.min(24, prompt.length)))) {

      score += 3;

    }

    for (const token of q.split(" ")) {

      if (token.length >= 2 && prompt.includes(token)) score += 1;

    }

    for (const rawKw of preset.keywords ?? []) {

      const kw = normalizeQueryText(rawKw);

      if (kw.length >= 2 && q.includes(kw)) score += 2;

      for (const token of q.split(" ")) {

        if (token.length >= 2 && kw.includes(token)) score += 1;

      }

    }

    if (!best || score > best.score) best = { id: preset.id, score };

  }

  if (best && best.score >= 2) return { preset_id: best.id, match: "text" };

  const lexical = resolvePresetFromLexicalIndex(q, lexicalIndex);

  if (lexical.preset_id) return { preset_id: lexical.preset_id, match: "lexical" };

  return { preset_id: null, match: "none" };

}



export async function resolvePresetIdAsync(

  presets: LogosStudioPreset[],

  opts: { preset_id?: string; query?: string },

  lexicalIndex?: LogosStudioLexicalIndex | null,

  embeddingIndex?: LogosStudioEmbeddingIndex | null,

): Promise<{ preset_id: string | null; match: "id" | "text" | "lexical" | "embedding" | "none" }> {

  const tier01 = resolvePresetId(presets, opts, lexicalIndex);

  if (tier01.match === "id") return tier01;

  if (tier01.preset_id?.startsWith("bigset_topic_")) return tier01;

  if (!opts.query?.trim()) return tier01;

  if (!logosStudioEmbeddingRouterEnabled()) return tier01;

  const index = embeddingIndex ?? (await loadLogosStudioEmbeddingIndex());

  if (!index.vectors?.length) return tier01;

  const encoded = await encodeLogosStudioQueryEmbedding(opts.query.trim());

  if (!encoded.ok) return tier01;

  const embedded = resolvePresetFromEmbeddingIndex(encoded.vector, index);

  if (!embedded.preset_id) return tier01;

  const weakTier01 =
    !tier01.preset_id ||
    tier01.preset_id.startsWith("era_") ||
    tier01.preset_id.startsWith("topic_");

  if (weakTier01) return { preset_id: embedded.preset_id, match: "embedding" };

  return tier01;

}



export async function buildStudioQueryResponse(presetId: string) {

  const [presetsDoc, routerDoc, taxonomyDoc] = await Promise.all([

    loadLogosStudioPresets(),

    loadLogosStudioRouter(),

    loadLogosStudioTaxonomy(),

  ]);

  const preset = presetsDoc.presets.find((p) => p.id === presetId);

  if (!preset) return null;



  const router = routerDoc.presets[presetId];

  const pathV1 = mergePresetRouterPath(preset, router);

  const mergedForHighlight = {

    highlight_node_ids: preset.highlight_node_ids,

    reasoning_path_v1: preset.reasoning_path_v1,

    router_path_v1: pathV1,

  };

  const highlightNodeIds = resolveHighlightNodeIds(mergedForHighlight);

  const reasoningPath =

    pathV1?.reasoning_path_v1 ?? preset.reasoning_path_v1 ?? null;

  const insightCard = taxonomyDoc.insight_cards?.[presetId] ?? null;



  return {

    schema: "logos_research_studio_query_v1",

    research_only: true,

    send_gate: "HOLD",

    non_gating: true,

    preset_id: preset.id,

    query: pathV1?.query ?? preset.prompt_ko,

    answer:
      preset.answer_ko?.trim() ||
      preset.answer_ko_product?.trim() ||
      "프리셋 응답을 불러오지 못했습니다.",

    path: {

      note_ko: pathV1?.note_ko ?? null,

      steps: pathV1?.path_steps ?? [],

      verse_refs: pathV1?.verse_refs ?? [],

      node_ids: pathV1?.node_ids ?? [],

      path_id: pathV1?.path_id ?? null,

      bridges_matched: pathV1?.bridges_matched ?? router?.router_summary?.bridges_matched ?? null,

      reasoning_path_v1: reasoningPath,

    },

    highlight_node_ids: highlightNodeIds,

    subgraph: {

      graph_slice_url: LOGOS_STUDIO_GRAPH_SLICE_URL,

      highlight_count: highlightNodeIds.length,

    },

    disclaimer: presetsDoc.disclaimer ?? null,

    insight_card: insightCard,

    reproduce_note:

      "Curated preset bundle · not live LLM · TSK full cross-ref Tier C · OSS: github.com/mkmlab-v2/mkm-universal-root",

  };

}



export type StudioQueryPayload = {
  schema: string;
  research_only: boolean;
  send_gate: string;
  non_gating: boolean;
  preset_id: string;
  query_mode?: string;
  query: string;
  answer: string;
  path: {
    note_ko: string | null;
    steps: string[];
    verse_refs: string[];
    node_ids?: string[];
    path_id?: string | null;
    bridges_matched: number | null;
    reasoning_path_v1?: LogosReasoningPathV1 | null;
  };
  highlight_node_ids: string[];
  subgraph?: {
    graph_slice_url: string;
    highlight_count: number;
  };
  disclaimer?: Record<string, unknown> | null;
  insight_card?: LogosStudioInsightCard | null;
  graphrag_meta?: {
    bridges_matched?: number;
    paths_count?: number;
    skipped?: boolean;
    paths_preview?: Array<{ path_id?: string; note_ko?: string; steps?: string[] }>;
  };
  conflict_context?: Extract<ConflictContextResult, { ok: true }> | null;
  synthesis_meta?: Extract<SynthesisResult, { ok: true }> | null;
  evidence_confidence?: {
    ecs_v1: number;
    band: "low" | "mid" | "high";
    components: {
      path_depth_ratio: number;
      cited_refs_strength: number;
      conflict_entropy_penalty: number;
    };
    note_ko: string;
    requery_poc?: boolean;
  };
  reproduce_note?: string;
};

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

function attachEvidenceConfidence(
  payload: StudioQueryPayload,
  opts?: { ecsExpandPoc?: boolean },
): StudioQueryPayload {
  const steps = payload.path.steps?.length ?? 0;
  const refs = payload.path.verse_refs?.length ?? 0;
  const depthDivisor = opts?.ecsExpandPoc ? 8 : 5;
  const pathDepthRatio = clamp01(steps / depthDivisor);
  const citedRefsStrength = clamp01(Math.tanh(refs / 4));
  const groups = payload.conflict_context?.groups ?? [];
  const groupCount = payload.conflict_context?.group_count ?? 0;
  const avgSchoolCount =
    groups.length > 0
      ? groups.reduce((acc, g) => acc + Number(g.school_count || 0), 0) / groups.length
      : 0;
  const conflictEntropyPenalty = clamp01((groupCount > 0 ? 0.25 : 0) + avgSchoolCount / 16);
  const ecsRaw = (0.4 * pathDepthRatio + 0.4 * citedRefsStrength - 0.2 * conflictEntropyPenalty) * 100;
  const ecs = Math.round(Math.max(0, Math.min(100, ecsRaw)));
  const band: "low" | "mid" | "high" = ecs >= 75 ? "high" : ecs >= 50 ? "mid" : "low";

  return {
    ...payload,
    evidence_confidence: {
      ecs_v1: ecs,
      band,
      components: {
        path_depth_ratio: Number(pathDepthRatio.toFixed(4)),
        cited_refs_strength: Number(citedRefsStrength.toFixed(4)),
        conflict_entropy_penalty: Number(conflictEntropyPenalty.toFixed(4)),
      },
      note_ko: opts?.ecsExpandPoc
        ? "ECS v1 PoC — 경로 깊이 확장 재조회 적용 · Track A 승격·실행 신호 아님."
        : "ECS v1은 구조 신뢰도 지표이며 Track A 승격·실행 신호가 아닙니다.",
      ...(opts?.ecsExpandPoc ? { requery_poc: true as const } : {}),
    },
  };
}



export async function buildDynamicGraphragStudioResponse(

  query: string,

  graphrag: Extract<GraphragEncodeResult, { ok: true }>,

) {

  const presetsDoc = await loadLogosStudioPresets();

  const rp = graphrag.router_path_v1;

  const highlightNodeIds =

    graphrag.highlight_node_ids.length > 0

      ? graphrag.highlight_node_ids

      : resolveHighlightNodeIds({ highlight_node_ids: [], router_path_v1: rp });



  const gapKo =

    "전량 TSK 교차참조(63,779)는 Tier C 로드맵 — 본 스튜디오는 query-time GraphRAG·부분 그래프입니다.";



  return {

    schema: "logos_research_studio_query_v1",

    research_only: true,

    send_gate: "HOLD",

    non_gating: true,

    preset_id: "dynamic_graphrag",

    query_mode: "graphrag_only",

    query,

    answer: graphrag.answer_ko,

    path: {

      note_ko: rp.note_ko ?? null,

      steps: rp.path_steps ?? [],

      verse_refs: rp.verse_refs ?? [],

      node_ids: rp.node_ids ?? [],

      path_id: rp.path_id ?? null,

      bridges_matched: graphrag.bridges_matched,

      reasoning_path_v1: rp.reasoning_path_v1 ?? null,

    },

    highlight_node_ids: highlightNodeIds,

    subgraph: {

      graph_slice_url: LOGOS_STUDIO_GRAPH_SLICE_URL,

      highlight_count: highlightNodeIds.length,

    },

    disclaimer: presetsDoc.disclaimer ?? null,

    insight_card: {

      preset_id: "dynamic_graphrag",

      slot: "query_time",

      slot_label_ko: "query-time GraphRAG",

      one_liner_ko: `bridges ${graphrag.bridges_matched} · paths ${graphrag.paths_count} · citation lock`,

      verse_anchors: rp.verse_refs ?? [],

      gap_ko: gapKo,

      governance: "[HYPO][NON_GATING]",

    },

    graphrag_meta: {

      bridges_matched: graphrag.bridges_matched,

      paths_count: graphrag.paths_count,

      paths_preview: graphrag.paths_preview,

    },

    reproduce_note:

      "Query-time subgraph GraphRAG · not live LLM · TSK Tier C · OSS: github.com/mkmlab-v2/mkm-universal-root",

  };

}



export function enrichStudioQueryWithGraphrag(

  payload: StudioQueryPayload,

  query: string,

  graphrag: Extract<GraphragEncodeResult, { ok: true }>,

): StudioQueryPayload {

  const rp = graphrag.router_path_v1;

  const staticScore = payload.path.bridges_matched ?? 0;

  const dynamicScore = graphrag.bridges_matched;

  const customQuery = query.trim() !== (payload.query || "").trim();

  const shouldOverlay =

    customQuery ||

    dynamicScore > staticScore ||

    (rp.verse_refs?.length ?? 0) > (payload.path.verse_refs?.length ?? 0);



  if (!shouldOverlay) {

    return {

      ...payload,

      query_mode: "preset",

      graphrag_meta: { skipped: true, bridges_matched: dynamicScore },

    };

  }



  const mergedHighlight = [

    ...new Set([...(rp.node_ids || []), ...(payload.highlight_node_ids || [])]),

  ].slice(0, 48);



  return {

    ...payload,

    query_mode: customQuery ? "preset+graphrag_custom" : "preset+graphrag",

    query: query.trim() || payload.query,

    answer: customQuery ? graphrag.answer_ko : payload.answer,

    path: {

      note_ko: rp.note_ko ?? payload.path.note_ko,

      steps: rp.path_steps ?? payload.path.steps,

      verse_refs: rp.verse_refs ?? payload.path.verse_refs,

      node_ids: rp.node_ids ?? payload.path.node_ids,

      path_id: rp.path_id ?? payload.path.path_id,

      bridges_matched: Math.max(dynamicScore, staticScore),

      reasoning_path_v1: rp.reasoning_path_v1 ?? payload.path.reasoning_path_v1,

    },

    highlight_node_ids: mergedHighlight.length ? mergedHighlight : payload.highlight_node_ids,

    graphrag_meta: {

      bridges_matched: graphrag.bridges_matched,

      paths_count: graphrag.paths_count,

      paths_preview: graphrag.paths_preview,

    },

  };

}



export async function buildStudioQueryWithGraphrag(
  presetId: string | null,
  query: string,
  opts?: { ecsExpandPoc?: boolean },
): Promise<StudioQueryPayload | null> {

  const q = query.trim();

  let payload: StudioQueryPayload | null = null;

  if (presetId) {

    payload = (await buildStudioQueryResponse(presetId)) as StudioQueryPayload | null;

  }

  if (logosStudioGraphragRouterEnabled() && q) {

    const graphrag = await encodeLogosStudioQueryGraphrag(q);

    if (graphrag.ok) {

      if (!payload) {

        payload = await buildDynamicGraphragStudioResponse(q, graphrag);

      } else {

        payload = enrichStudioQueryWithGraphrag(payload, q, graphrag);

      }

    }

  }

  if (payload && logosStudioConflictRetrievalEnabled() && q) {

    const conflict = await retrieveLogosStudioConflictContext(q, payload.preset_id);

    if (conflict.ok && conflict.group_count > 0) {

      payload = { ...payload, conflict_context: conflict };

    } else {

      payload = { ...payload, conflict_context: null };

    }

  }

  if (
    payload &&
    logosStudioDynamicSynthesisEnabled() &&
    payload.conflict_context?.group_count &&
    q
  ) {
    const synthesis = await synthesizeLogosStudioDynamicAnswer(payload, q);
    if (synthesis.ok && synthesis.citation_valid !== false) {
      const patch = synthesis.insight_patch;
      const baseMode = payload.query_mode || "preset";
      payload = {
        ...payload,
        answer: synthesis.answer_ko,
        synthesis_meta: synthesis,
        insight_card: {
          preset_id: payload.preset_id,
          slot: payload.insight_card?.slot ?? "dynamic_synthesis",
          slot_label_ko: payload.insight_card?.slot_label_ko ?? "동적 합성",
          one_liner_ko: patch?.one_liner_ko ?? payload.insight_card?.one_liner_ko,
          verse_anchors: payload.path.verse_refs?.slice(0, 12),
          gap_ko: patch?.gap_ko ?? payload.insight_card?.gap_ko,
          governance: patch?.governance ?? payload.insight_card?.governance,
        },
        query_mode: `${baseMode}+synthesis`,
      };
    } else if (synthesis.ok) {
      payload = { ...payload, synthesis_meta: null };
    }
  }

  return payload ? attachEvidenceConfidence(payload, opts) : payload;

}



export async function listPresetSummaries(presets: LogosStudioPreset[]) {

  const taxonomy = await loadLogosStudioTaxonomy();

  return presets.map((p) => {

    const card = taxonomy.insight_cards?.[p.id];

    return {

      id: p.id,

      prompt_ko: p.prompt_ko,

      slot: card?.slot ?? null,

      slot_label_ko: card?.slot_label_ko ?? null,

    };

  });

}


