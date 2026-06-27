import type { LensContextMeshHopIndexDoc } from "@/lib/lensContextMeshBfsV1";

import { KIND_COLOR, type LogosGraphSliceDoc } from "@/lib/logosResearchGraphTypesV1";

import { seedCircularPositions } from "@/lib/logosResearchGraphLayoutV1";

import {

  normalizeRefKey,

  type LogosGraphSliceNode,

} from "@/lib/logosResearchHighlightV1";



export const EXPLORE_MESH_INITIAL_MAX = 72;

export const EXPLORE_MESH_EXPAND_MAX = 160;

export const EXPLORE_MESH_CLICK_EXPAND_HOPS = 1;

/** Below this visible count, skip full-canvas fitView (pivot zoom instead). */

export const EXPLORE_FIT_VIEW_MIN_NODES = 30;



export const GHOST_NODE_PREFIX = "ghost::verse::";



export type ExplorePositionCache = Map<string, { x: number; y: number }>;



export type ExploreMeshSnapshot = {

  ids: string[];

  idToIndex: Map<string, number>;

  positions: Float32Array;

  links: Float32Array;

  colors: Float32Array;

  sizes: Float32Array;

  linkWidths: Float32Array;

  ghostCount: number;

};



function hexToRgba(hex: string, alpha: number): [number, number, number, number] {

  const h = hex.replace("#", "");

  const r = parseInt(h.slice(0, 2), 16) / 255;

  const g = parseInt(h.slice(2, 4), 16) / 255;

  const b = parseInt(h.slice(4, 6), 16) / 255;

  return [r, g, b, alpha];

}



export function ghostNodeIdForRef(ref: string): string {

  return `${GHOST_NODE_PREFIX}${normalizeRefKey(ref)}`;

}



export function isGhostNodeId(id: string): boolean {

  return id.startsWith(GHOST_NODE_PREFIX);

}



export function buildGhostVerseNode(ref: string): LogosGraphSliceNode {

  return {

    id: ghostNodeIdForRef(ref),

    kind: "ghost",

    label: ref,

    ref,

    hub_score: 0.12,

  };

}



function spineEdgeSet(pathSpineIds: string[]): Set<string> {

  const pairs = new Set<string>();

  for (let i = 0; i < pathSpineIds.length - 1; i += 1) {

    pairs.add(`${pathSpineIds[i]}|${pathSpineIds[i + 1]}`);

    pairs.add(`${pathSpineIds[i + 1]}|${pathSpineIds[i]}`);

  }

  return pairs;

}



/** Merge cached coords with ring placement for newly visible nodes. */

export function resolveExplorePositions(

  nodes: LogosGraphSliceNode[],

  cache: ExplorePositionCache,

  opts: {

    focusId?: string | null;

    pathSpineIds?: string[];

    radius?: number;

  } = {},

): ExplorePositionCache {

  const ids = nodes.map((n) => n.id);

  const missing = ids.filter((id) => !cache.has(id));

  const out = new Map<string, { x: number; y: number }>();



  for (const id of ids) {

    const cached = cache.get(id);

    if (cached) out.set(id, cached);

  }



  if (!out.size && missing.length === ids.length) {

    const seeded = seedCircularPositions(nodes, opts.radius ?? 220 + Math.min(nodes.length, 120) * 2.2);

    for (const p of seeded) out.set(p.id, { x: p.x, y: p.y });

    return out;

  }



  if (!missing.length) return out;



  const spine = opts.pathSpineIds || [];

  const anchorId =

    (opts.focusId && out.has(opts.focusId) ? opts.focusId : null) ??

    spine.find((id) => out.has(id)) ??

    ids.find((id) => out.has(id)) ??

    null;

  const anchor = anchorId ? out.get(anchorId)! : { x: 0, y: 0 };

  const baseR = opts.radius ?? 148;



  missing.forEach((id, index) => {

    const angle = (2 * Math.PI * index) / Math.max(missing.length, 1) - Math.PI / 2;

    const ring = baseR + (index % 3) * 34;

    out.set(id, {

      x: anchor.x + Math.cos(angle) * ring,

      y: anchor.y + Math.sin(angle) * ring,

    });

  });



  return out;

}



export function snapshotPositionsToCache(

  snapshot: ExploreMeshSnapshot,

): ExplorePositionCache {

  const cache: ExplorePositionCache = new Map();

  snapshot.ids.forEach((id, index) => {

    cache.set(id, {

      x: snapshot.positions[index * 2],

      y: snapshot.positions[index * 2 + 1],

    });

  });

  return cache;

}



export function hopDistanceMap(

  hopIndex: LensContextMeshHopIndexDoc,

  seedId: string,

  maxHops = 8,

): Map<string, number> {

  const nodes = hopIndex.nodes || {};

  const dist = new Map<string, number>();

  if (!nodes[seedId]) return dist;

  const queue: Array<{ id: string; d: number }> = [{ id: seedId, d: 0 }];

  dist.set(seedId, 0);

  while (queue.length) {

    const { id, d } = queue.shift()!;

    if (d >= maxHops) continue;

    for (const nb of nodes[id]?.neighbors || []) {

      const nid = nb.id;

      if (!nid || dist.has(nid)) continue;

      dist.set(nid, d + 1);

      queue.push({ id: nid, d: d + 1 });

    }

  }

  return dist;

}



export function expandVisibleFromClick(

  hopIndex: LensContextMeshHopIndexDoc,

  visible: Set<string>,

  nodeId: string,

  maxNodes: number,

): Set<string> {

  const next = new Set(visible);

  const neighbors = hopIndex.nodes[nodeId]?.neighbors || [];

  for (const nb of neighbors) {

    if (nb.id) next.add(nb.id);

  }

  if (next.size <= maxNodes) return next;

  const ordered = [...next];

  const keep = new Set<string>();

  if (ordered.includes(nodeId)) keep.add(nodeId);

  for (const id of ordered) {

    if (keep.size >= maxNodes) break;

    keep.add(id);

  }

  return keep;

}



export function decayAlpha(hop: number, zeta = 0.42, minAlpha = 0.12): number {

  return Math.max(minAlpha, Math.exp(-zeta * hop));

}



export function decayScale(hop: number, zeta = 0.28, minScale = 0.22, base = 1): number {

  return Math.max(minScale, base * Math.exp(-zeta * hop));

}



export function buildExploreMeshSnapshot(

  graphDoc: LogosGraphSliceDoc,

  visibleIds: Set<string>,

  opts: {

    pathSpineIds?: string[];

    highlightIds?: string[];

    focusId?: string | null;

    hopDistances?: Map<string, number>;

    ghostRefs?: string[];

    activeGhostRef?: string | null;

    positionCache?: ExplorePositionCache;

    ghostAnchorId?: string | null;

  } = {},

): ExploreMeshSnapshot | null {

  const sliceNodes = (graphDoc.nodes || []).filter((n) => visibleIds.has(n.id));

  const ghostRefs = (opts.ghostRefs || []).filter(Boolean);

  const ghostNodes = ghostRefs.map((ref) => buildGhostVerseNode(ref));

  const nodes = [...sliceNodes, ...ghostNodes];

  if (!nodes.length) return null;



  const ids = nodes.map((n) => n.id);

  const idToIndex = new Map(ids.map((id, i) => [id, i]));

  const spineEdges = spineEdgeSet(opts.pathSpineIds || []);

  const highlight = new Set(opts.highlightIds || []);

  const focusId = opts.focusId || null;

  const activeGhostRef = opts.activeGhostRef || null;

  const hopDistances = opts.hopDistances || new Map<string, number>();

  const cache = opts.positionCache || new Map();



  const ghostAnchorId =

    opts.ghostAnchorId ||

    focusId ||

    (opts.pathSpineIds || []).find((id) => visibleIds.has(id)) ||

    sliceNodes[0]?.id ||

    null;



  const posById = resolveExplorePositions(nodes, cache, {

    focusId: focusId || ghostAnchorId,

    pathSpineIds: opts.pathSpineIds,

    radius: 220 + Math.min(sliceNodes.length, 120) * 2.2,

  });



  const positions = new Float32Array(nodes.length * 2);

  const colors = new Float32Array(nodes.length * 4);

  const sizes = new Float32Array(nodes.length);



  nodes.forEach((node, index) => {

    const pos = posById.get(node.id);

    positions[index * 2] = pos?.x ?? 0;

    positions[index * 2 + 1] = pos?.y ?? 0;



    const isGhost = isGhostNodeId(node.id);

    const kind = node.kind || "other";

    const baseHex = KIND_COLOR[kind] || KIND_COLOR.other;

    const isHighlight = highlight.has(node.id);

    const isFocus = focusId === node.id;

    const isSpine = (opts.pathSpineIds || []).includes(node.id);

    const isActiveGhost =

      isGhost && activeGhostRef && ghostNodeIdForRef(activeGhostRef) === node.id;



    let alpha = 0.72;

    if (isGhost) {

      alpha = isActiveGhost ? 0.58 : 0.34;

    } else if (isFocus) alpha = 1;

    else if (isHighlight) alpha = 0.96;

    else if (isSpine) alpha = 0.9;

    else if (focusId) alpha = decayAlpha(hopDistances.get(node.id) ?? 6, 0.32, 0.38);

    else alpha = decayAlpha(hopDistances.get(node.id) ?? 0, 0.1, 0.58);



    const [r, g, b] = hexToRgba(baseHex, 1);

    colors[index * 4] = r;

    colors[index * 4 + 1] = g;

    colors[index * 4 + 2] = b;

    colors[index * 4 + 3] = alpha;



    const hub = isGhost ? 3.2 : 4 + (node.hub_score || 0) * 7;

    const scale = isGhost

      ? isActiveGhost

        ? 0.92

        : 0.72

      : isFocus

        ? 1.35

        : isHighlight

          ? 1.18

          : decayScale(hopDistances.get(node.id) ?? (focusId ? 6 : 0), 0.24, 0.35, 1);

    sizes[index] = hub * scale;

  });



  const linkPairs: number[] = [];

  const linkWidths: number[] = [];



  for (const edge of graphDoc.edges || []) {

    const si = idToIndex.get(edge.src);

    const ti = idToIndex.get(edge.dst);

    if (si == null || ti == null) continue;

    linkPairs.push(si, ti);

    const spineHit = spineEdges.has(`${edge.src}|${edge.dst}`);

    const touch = highlight.has(edge.src) && highlight.has(edge.dst);

    linkWidths.push(spineHit ? 2.4 : touch ? 1.6 : 0.55);

  }



  if (ghostAnchorId && ghostNodes.length) {

    const anchorIdx = idToIndex.get(ghostAnchorId);

    if (anchorIdx != null) {

      for (const ghost of ghostNodes) {

        const gi = idToIndex.get(ghost.id);

        if (gi == null) continue;

        linkPairs.push(anchorIdx, gi);

        const active = activeGhostRef && ghostNodeIdForRef(activeGhostRef) === ghost.id;

        linkWidths.push(active ? 0.85 : 0.38);

      }

    }

  }



  return {

    ids,

    idToIndex,

    positions,

    links: new Float32Array(linkPairs),

    colors,

    sizes,

    linkWidths: new Float32Array(linkWidths),

    ghostCount: ghostNodes.length,

  };

}



export function nodeLabel(node: LogosGraphSliceNode): string {

  if (isGhostNodeId(node.id)) {

    const ref = node.ref || node.label || node.id.replace(GHOST_NODE_PREFIX, "");

    return `[탐색 중] ${ref}`;

  }

  return node.label || node.ref || node.id.split("::").pop() || node.id;

}


