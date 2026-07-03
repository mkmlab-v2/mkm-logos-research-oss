/** Ask semantic graph sidecar — bounded subgraph from S1 citation lock (research_only · [NON_GATING]). */

import {
  buildRefToNodeIndex,
  resolveRefsToIds,
  type LogosGraphSliceNode,
} from "@/lib/logosResearchHighlightV1";
import type { LogosGraphSliceDoc } from "@/lib/logosResearchGraphTypesV1";
import type { LensContextMeshHopIndexDoc } from "@/lib/lensContextMeshBfsV1";
import { MINDMAP_MESH_DEFAULT_MAX } from "@/lib/logosResearchPathMindmapMeshV1";

/** Mirrors docs/final/artifacts/logos_ask_graph_sidecar_contract_v1_latest.json */
export const LOGOS_ASK_GRAPH_MAX_VERSE_REFS = 24;
export const LOGOS_ASK_GRAPH_MAX_MESH_NODES = MINDMAP_MESH_DEFAULT_MAX;
export const LOGOS_ASK_GRAPH_MESH_BFS_DEPTH = 2;
export const LOGOS_ASK_GRAPH_PULSE_DEBOUNCE_MS = 150;

const FORBIDDEN_SEED_RE =
  /repair_v2|combined_sum|vector_4d|hub_score|state16|Gematria_Pin|mispar_/i;

export type AskGraphStreamPhase = "idle" | "snapshot" | "s4" | "done";

export function isLogosAskGraphV1Enabled(): boolean {
  const raw = (process.env.NEXT_PUBLIC_LOGOS_ASK_GRAPH_V1 ?? "1").trim().toLowerCase();
  return raw !== "0" && raw !== "false" && raw !== "off";
}

export function collectAskGraphSeedRefs(
  verseRefs: string[],
  citationLockAnchors: string[] = [],
  max = LOGOS_ASK_GRAPH_MAX_VERSE_REFS,
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  const push = (raw: string) => {
    const t = String(raw || "").trim();
    if (!t || seen.has(t) || FORBIDDEN_SEED_RE.test(t)) return;
    seen.add(t);
    out.push(t);
  };
  for (const r of verseRefs) push(r);
  for (const a of citationLockAnchors) push(a);
  return out.slice(0, max);
}

export function resolveAskGraphSeedIds(
  seedRefs: string[],
  graphDoc: LogosGraphSliceDoc | null,
): string[] {
  const nodes = graphDoc?.nodes ?? [];
  if (!nodes.length || !seedRefs.length) return [];
  const refToNodeIds = buildRefToNodeIndex(nodes);
  return resolveRefsToIds(seedRefs, refToNodeIds).slice(0, LOGOS_ASK_GRAPH_MAX_MESH_NODES);
}

export function buildAskGraphNodeById(
  graphDoc: LogosGraphSliceDoc | null,
): Record<string, LogosGraphSliceNode> {
  const map: Record<string, LogosGraphSliceNode> = {};
  for (const n of graphDoc?.nodes ?? []) {
    if (n?.id) map[n.id] = n;
  }
  return map;
}

export type AskGraphMeshSummary = {
  graphDoc: LogosGraphSliceDoc;
  hopIndex: LensContextMeshHopIndexDoc;
  seedIds: string[];
  nodeById: Record<string, LogosGraphSliceNode>;
};

export function buildAskGraphMeshSummary(
  graphDoc: LogosGraphSliceDoc | null,
  hopIndex: LensContextMeshHopIndexDoc | null,
  seedIds: string[],
): AskGraphMeshSummary | null {
  if (!graphDoc?.nodes?.length || !hopIndex || !seedIds.length) return null;
  return {
    graphDoc,
    hopIndex,
    seedIds,
    nodeById: buildAskGraphNodeById(graphDoc),
  };
}

/** Contract v1: graph pulse on snapshot/done boundaries — not per SSE char. */
export function shouldPulseAskGraph(streamPhase?: AskGraphStreamPhase): boolean {
  return streamPhase === "snapshot" || streamPhase === "s4" || streamPhase === "done";
}

export const LOGOS_ASK_GRAPH_RENDER_NODE_BUDGET = 48;

export function exceedsAskGraphRenderBudget(nodeCount: number): boolean {
  return nodeCount > LOGOS_ASK_GRAPH_RENDER_NODE_BUDGET;
}

export type AskGraphVizMode = "full" | "path";

/** Path-only view strips mesh halo for clarity (focus mode). */
export function filterPathMindmapForVizMode(
  model: import("@/lib/pathMindmapCoreV1").PathMindmapModel,
  mode: AskGraphVizMode,
): import("@/lib/pathMindmapCoreV1").PathMindmapModel {
  if (mode !== "path") return model;
  const nodes = model.nodes.filter((n) => n.kind !== "mesh");
  const ids = new Set(nodes.map((n) => n.id));
  const edges = model.edges.filter((e) => ids.has(e.from) && ids.has(e.to));
  return { ...model, nodes, edges };
}

function normalizeRefKey(ref: string): string {
  return String(ref || "")
    .trim()
    .replace(/\s+/g, "");
}

/** PUBLIC trust tooltips — citation lock only; no repair_v2 / hub_score. */
export function buildAskGraphNodeTooltips(
  model: import("@/lib/pathMindmapCoreV1").PathMindmapModel,
  verseRefs: string[],
  citationLockAnchors: string[] = [],
  nodeById: Record<string, LogosGraphSliceNode> = {},
): Record<string, string> {
  const verseSet = new Set(verseRefs.map(normalizeRefKey));
  const tips: Record<string, string> = {};

  for (const node of model.nodes) {
    if (node.kind === "verse") {
      const locked = verseSet.has(normalizeRefKey(node.label));
      const anchorHit = citationLockAnchors.some(
        (a) => !FORBIDDEN_SEED_RE.test(a) && normalizeRefKey(a) === normalizeRefKey(node.label),
      );
      tips[node.id] = locked || anchorHit
        ? `고정 구절 · ${node.label}`
        : `구절 경로 · ${node.label}`;
    } else if (node.kind === "mesh") {
      const sliceNode = node.graphNodeId ? nodeById[node.graphNodeId] : undefined;
      const label = sliceNode?.label || node.label || "연결";
      tips[node.id] = `연결 요약 · ${label}`;
    } else if (node.kind === "root") {
      tips[node.id] = "질의 중심 · 경로 탐색";
    } else {
      tips[node.id] = `${node.label} · spine`;
    }
  }

  return tips;
}
