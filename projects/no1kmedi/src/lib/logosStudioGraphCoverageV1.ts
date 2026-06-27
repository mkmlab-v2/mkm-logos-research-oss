import {
  buildRefToNodeIndex,
  nodeIdsForRef,
  normalizeRefKey,
  type LogosGraphSliceNode,
} from "@/lib/logosResearchHighlightV1";
import type { LensContextMeshHopIndexDoc } from "@/lib/lensContextMeshBfsV1";

export const GRAPH_COVERAGE_MIN_RATIO = 0.5;
export const GRAPH_MIN_VISIBLE_NODES = 4;

export type GraphSliceCoverage = {
  totalVerseRefs: number;
  mappedVerseRefs: number;
  ratio: number;
  mappedNodeIds: string[];
  unmappedRefs: string[];
};

export function routerStubNodeIdForRef(ref: string): string {
  return `showroom_router_stub_verse::${normalizeRefKey(ref)}`;
}

/** Merge hop-index router verse stubs so path cites map in explore + chips (commercial demo). */
export function augmentGraphNodesWithRouterStubs(
  nodes: LogosGraphSliceNode[],
  hopIndex: LensContextMeshHopIndexDoc | null,
  verseRefs: string[],
): LogosGraphSliceNode[] {
  const hopNodes = hopIndex?.nodes;
  if (!hopNodes) return nodes;
  const out = [...nodes];
  const seen = new Set(nodes.map((n) => n.id));
  for (const ref of verseRefs) {
    const stubId = routerStubNodeIdForRef(ref);
    if (stubId in hopNodes && !seen.has(stubId)) {
      const key = normalizeRefKey(ref);
      out.push({ id: stubId, kind: "verse", ref: key, label: ref });
      seen.add(stubId);
    }
  }
  return out;
}

export function computeGraphSliceCoverage(
  nodes: LogosGraphSliceNode[],
  verseRefs: string[],
  highlightNodeIds: string[] = [],
): GraphSliceCoverage {
  const refIndex = buildRefToNodeIndex(nodes);
  const nodeIdSet = new Set(nodes.map((n) => n.id));
  const unmappedRefs: string[] = [];
  const mappedNodeIds: string[] = [];
  let mappedVerseRefs = 0;

  for (const ref of verseRefs) {
    const ids = nodeIdsForRef(ref, refIndex).filter((id) => nodeIdSet.has(id));
    if (ids.length) {
      mappedVerseRefs += 1;
      for (const id of ids) {
        if (!mappedNodeIds.includes(id)) mappedNodeIds.push(id);
      }
    } else {
      unmappedRefs.push(ref);
    }
  }

  for (const id of highlightNodeIds) {
    if (nodeIdSet.has(id) && !mappedNodeIds.includes(id)) mappedNodeIds.push(id);
  }

  const total = verseRefs.length;
  const ratio =
    total > 0
      ? mappedVerseRefs / total
      : mappedNodeIds.length > 0
        ? 1
        : 0;

  return {
    totalVerseRefs: total,
    mappedVerseRefs,
    ratio,
    mappedNodeIds,
    unmappedRefs,
  };
}

/** Force-graph only when slice actually covers the cited path. */
export function shouldShowForceGraph(
  coverage: GraphSliceCoverage,
  visibleNodeCount: number,
): boolean {
  return (
    coverage.ratio >= GRAPH_COVERAGE_MIN_RATIO &&
    visibleNodeCount >= GRAPH_MIN_VISIBLE_NODES &&
    coverage.mappedNodeIds.length >= 2
  );
}
