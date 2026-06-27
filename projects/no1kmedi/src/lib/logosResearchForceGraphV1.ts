import type { LogosGraphSliceNode } from "./logosResearchHighlightV1";

import { KIND_COLOR, type LogosGraphSliceDoc } from "./logosResearchGraphTypesV1";
import { seedTopologyLayout } from "./logosResearchGraphLayoutV1";

export type ForceGraphNode = {
  id: string;
  name: string;
  kind: string;
  hub_score: number;
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
};

export type ForceGraphLink = {
  source: string;
  target: string;
  spine?: boolean;
};

export type ForceGraphData = {
  nodes: ForceGraphNode[];
  links: ForceGraphLink[];
};

function spineEdgeSet(pathSpineIds: string[]): Set<string> {
  const pairs = new Set<string>();
  for (let i = 0; i < pathSpineIds.length - 1; i += 1) {
    pairs.add(`${pathSpineIds[i]}|${pathSpineIds[i + 1]}`);
    pairs.add(`${pathSpineIds[i + 1]}|${pathSpineIds[i]}`);
  }
  return pairs;
}

export function buildForceGraphData(
  graphDoc: LogosGraphSliceDoc,
  pathSpineIds: string[] = [],
  highlightIds: string[] = [],
): ForceGraphData {
  const spine = spineEdgeSet(pathSpineIds);
  const sliceNodes = graphDoc.nodes || [];
  const seeded = seedTopologyLayout(sliceNodes, pathSpineIds, highlightIds);
  const posById = new Map(seeded.map((p) => [p.id, p]));

  const nodes: ForceGraphNode[] = sliceNodes.map((n) => {
    const pos = posById.get(n.id);
    const x = pos?.x ?? 0;
    const y = pos?.y ?? 0;
    return {
      id: n.id,
      name: n.label || n.ref || n.id.split("::").pop() || n.id,
      kind: n.kind || "other",
      hub_score: n.hub_score || 0,
      x,
      y,
      fx: x,
      fy: y,
    };
  });
  const links: ForceGraphLink[] = (graphDoc.edges || []).map((e) => ({
    source: e.src,
    target: e.dst,
    spine: spine.has(`${e.src}|${e.dst}`),
  }));
  return { nodes, links };
}

export function nodeRadius(
  node: ForceGraphNode,
  highlight: boolean,
  pulse: boolean,
  pulsePhase = 0,
  hasHighlight = false,
): number {
  const base = 4.2 + node.hub_score * 6.2;
  if (pulse) {
    const breathe = 1 + 0.1 * Math.sin(pulsePhase * 5.5);
    return base * 1.55 * breathe;
  }
  if (highlight) return base * 1.32;
  if (hasHighlight) return base * 0.72;
  return base;
}

export function nodeColor(
  node: ForceGraphNode,
  highlight: boolean,
  pulse: boolean,
  hasHighlight: boolean,
  spine = false,
): string {
  const base = KIND_COLOR[node.kind] || KIND_COLOR.other;
  if (pulse) return "#ffffff";
  if (highlight) return base;
  if (spine && hasHighlight) return base;
  if (hasHighlight) return `${base}1a`;
  return `${base}4d`;
}

export function linkColor(
  link: ForceGraphLink,
  sourceId: string,
  targetId: string,
  highlight: Set<string>,
  pulse: Set<string>,
  hasHighlight: boolean,
): string {
  const pulseEdge = pulse.has(sourceId) || pulse.has(targetId);
  const active = highlight.has(sourceId) && highlight.has(targetId);
  const touch = highlight.has(sourceId) || highlight.has(targetId);
  if (pulseEdge) return "rgba(255,255,255,0.92)";
  if (link.spine && hasHighlight) return "rgba(252,211,77,0.9)";
  if (active) return "rgba(197,160,87,0.78)";
  if (touch && hasHighlight) return "rgba(197,160,87,0.32)";
  return hasHighlight ? "rgba(71,85,105,0.05)" : "rgba(148,163,184,0.14)";
}

export function linkWidth(
  link: ForceGraphLink,
  sourceId: string,
  targetId: string,
  highlight: Set<string>,
  pulse: Set<string>,
  hasHighlight: boolean,
): number {
  const pulseEdge = pulse.has(sourceId) || pulse.has(targetId);
  const active = highlight.has(sourceId) && highlight.has(targetId);
  const touch = highlight.has(sourceId) || highlight.has(targetId);
  if (pulseEdge) return 2.4;
  if (link.spine && hasHighlight) return 2.1;
  if (active) return 1.8;
  if (touch && hasHighlight) return 1.1;
  return hasHighlight ? 0.35 : 0.55;
}

export function freezeGraphNodes(nodes: ForceGraphNode[]): void {
  for (const node of nodes) {
    if (typeof node.x === "number" && typeof node.y === "number") {
      node.fx = node.x;
      node.fy = node.y;
    }
  }
}

export function releaseGraphNodes(nodes: ForceGraphNode[]): void {
  for (const node of nodes) {
    node.fx = undefined;
    node.fy = undefined;
  }
}

export function topHubNodeIds(nodes: LogosGraphSliceNode[], limit = 8): Set<string> {
  return new Set(
    nodes
      .filter((n) => n.kind === "verse")
      .sort((a, b) => (b.hub_score || 0) - (a.hub_score || 0))
      .slice(0, limit)
      .map((n) => n.id),
  );
}
