/**
 * Logos Ask lemma / betweenness layer v0 — Fact-Lock consumer helpers.
 * Loads REAL public JSON (no static import into RSC/client graph).
 * SAMPLE topology UI ≠ this REAL pack+lemma-index layer. send_gate HOLD.
 */

export type LemmaBetweennessVerseHubV0 = {
  id: string;
  kind: "verse";
  degree: number;
  approx_betweenness: number | null;
  in_pack_seed?: boolean;
  degree_norm?: number;
  betweenness_norm?: number;
};

export type LemmaBetweennessLayerV0 = {
  schema: string;
  version?: string;
  send_gate?: string;
  research_only?: boolean;
  ok?: boolean;
  data_class?: string;
  sparse_hold?: boolean;
  metric_primary?: string;
  metric_secondary?: string;
  hubs?: {
    verses?: LemmaBetweennessVerseHubV0[];
    lemmas?: Array<{ id: string; degree: number }>;
  };
  verse_lookup?: Record<
    string,
    { degree: number; approx_betweenness: number | null; in_pack_seed?: boolean }
  >;
  edges_preview?: Array<{
    src: string;
    dst: string;
    edge_class?: string;
    data_class?: string;
    weight?: number;
  }>;
  empty_map_spine?: { labels?: string[]; top_bridge_verses?: string[] };
  residuals_hard10?: string[];
  honesty?: { note?: string; theological_context_map_complete?: boolean };
  graph_stats?: {
    subgraph_node_count?: number;
    subgraph_edge_count?: number;
    max_approx_betweenness?: number;
  };
};

export const LEMMA_BETWEENNESS_LAYER_V0_URL =
  "/data/logos_studio/ask_lemma_betweenness_layer_v0.json";

let cached: LemmaBetweennessLayerV0 | null = null;
let inflight: Promise<LemmaBetweennessLayerV0 | null> | null = null;

export function lemmaLayerIsRealV0(layerDoc: LemmaBetweennessLayerV0 | null | undefined): boolean {
  if (!layerDoc) return false;
  return (
    layerDoc.ok === true &&
    layerDoc.data_class === "REAL_PACK_AND_LEMMA_INDEX" &&
    layerDoc.sparse_hold === false &&
    layerDoc.send_gate === "HOLD"
  );
}

export function lookupVerseLemmaMetricsV0(
  verseRef: string,
  layerDoc: LemmaBetweennessLayerV0 | null | undefined,
): { degree: number; approx_betweenness: number | null } | null {
  if (!layerDoc) return null;
  const key = verseRef.trim();
  if (!key) return null;
  const row = layerDoc.verse_lookup?.[key];
  if (!row) return null;
  return { degree: row.degree, approx_betweenness: row.approx_betweenness };
}

export function lemmaLayerGrammarAttrV0(layerDoc: LemmaBetweennessLayerV0 | null | undefined): string {
  if (lemmaLayerIsRealV0(layerDoc)) return "real_v0_hold";
  if (layerDoc?.sparse_hold) return "sparse_hold";
  return "sample_hold";
}

export function getCachedLogosAskLemmaBetweennessLayerV0(): LemmaBetweennessLayerV0 | null {
  return cached;
}

export async function loadLogosAskLemmaBetweennessLayerV0(
  init?: RequestInit,
): Promise<LemmaBetweennessLayerV0 | null> {
  if (cached) return cached;
  if (inflight) return inflight;
  inflight = (async () => {
    try {
      const res = await fetch(LEMMA_BETWEENNESS_LAYER_V0_URL, {
        ...init,
        headers: { Accept: "application/json", ...(init?.headers || {}) },
      });
      if (!res.ok) return null;
      const doc = (await res.json()) as LemmaBetweennessLayerV0;
      if (doc?.schema !== "logos_ask_lemma_betweenness_layer_v0") return null;
      cached = doc;
      return doc;
    } catch {
      return null;
    } finally {
      inflight = null;
    }
  })();
  return inflight;
}
