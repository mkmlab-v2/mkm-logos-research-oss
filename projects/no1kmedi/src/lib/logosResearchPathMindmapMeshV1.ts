/** Mesh summary layer for path mindmap — BFS local graph halo (research_only · [HYPO]). */

import { bfsVisibleNodeIds, type LensContextMeshHopIndexDoc } from "@/lib/lensContextMeshBfsV1";
import type { LogosGraphSliceDoc } from "@/lib/logosResearchGraphTypesV1";
import {
  nodeLabelFromSlice,
  type LogosGraphSliceNode,
} from "@/lib/logosResearchHighlightV1";
import {
  truncateMindmapLabel,
  type MindmapEdge,
  type PathMindmapModel,
} from "@/lib/pathMindmapCoreV1";

export const MINDMAP_MESH_DEFAULT_DEPTH = 2;
export const MINDMAP_MESH_DEFAULT_MAX = 40;

export type MindmapMeshSummaryInput = {
  base: PathMindmapModel;
  graphDoc: LogosGraphSliceDoc | null;
  hopIndex: LensContextMeshHopIndexDoc | null;
  seedIds: string[];
  nodeById?: Record<string, LogosGraphSliceNode>;
  maxMesh?: number;
  meshDepth?: number;
};

function mmMeshId(sliceId: string): string {
  return `mm:mesh:${sliceId}`;
}

function collectPathGraphIds(base: PathMindmapModel): Set<string> {
  const ids = new Set<string>();
  for (const n of base.nodes) {
    if (n.graphNodeId) ids.add(n.graphNodeId);
    if (n.kind === "verse") ids.add(n.label.replace(/\s+/g, ""));
  }
  return ids;
}

function resolveMmNodeId(sliceId: string, idMap: Map<string, string>): string | null {
  return idMap.get(sliceId) ?? null;
}

export function buildMindmapMeshSummary(input: MindmapMeshSummaryInput): {
  model: PathMindmapModel;
  meshShown: number;
  meshTotal: number;
} {
  const {
    base,
    graphDoc,
    hopIndex,
    seedIds,
    nodeById = {},
    maxMesh = MINDMAP_MESH_DEFAULT_MAX,
    meshDepth = MINDMAP_MESH_DEFAULT_DEPTH,
  } = input;

  const meshTotal = graphDoc?.nodes?.length ?? 0;
  if (!graphDoc?.nodes?.length || !hopIndex || !seedIds.length) {
    return { model: base, meshShown: 0, meshTotal };
  }

  const visible = bfsVisibleNodeIds(hopIndex, seedIds, meshDepth, maxMesh);
  const pathGraphIds = collectPathGraphIds(base);
  const idMap = new Map<string, string>();
  for (const n of base.nodes) {
    if (n.graphNodeId) idMap.set(n.graphNodeId, n.id);
  }

  const nodes = [...base.nodes];
  const edges: MindmapEdge[] = [...base.edges];
  const existing = new Set(nodes.map((n) => n.id));
  let meshShown = 0;

  for (const sliceId of visible) {
    if (pathGraphIds.has(sliceId)) {
      if (!idMap.has(sliceId)) {
        const hit = base.nodes.find((n) => n.graphNodeId === sliceId);
        if (hit) idMap.set(sliceId, hit.id);
      }
      continue;
    }
    const mmId = mmMeshId(sliceId);
    if (existing.has(mmId)) continue;
    const sliceNode = nodeById[sliceId] || graphDoc.nodes?.find((n) => n.id === sliceId);
    const label = truncateMindmapLabel(
      nodeLabelFromSlice(sliceId, nodeById) || sliceNode?.label || sliceId.split("::").pop() || sliceId,
      14,
    );
    nodes.push({
      id: mmId,
      label,
      kind: "mesh",
      depth: 3,
      parentId: base.rootId,
      graphNodeId: sliceId,
    });
    idMap.set(sliceId, mmId);
    existing.add(mmId);
    meshShown += 1;
  }

  const edgeKeys = new Set(edges.map((e) => `${e.from}|${e.to}`));
  for (const e of graphDoc.edges || []) {
    const from = resolveMmNodeId(e.src, idMap);
    const to = resolveMmNodeId(e.dst, idMap);
    if (!from || !to || from === to) continue;
    const key = `${from}|${to}`;
    if (edgeKeys.has(key)) continue;
    edgeKeys.add(key);
    edges.push({ from, to });
  }

  return { model: { ...base, nodes, edges }, meshShown, meshTotal };
}
