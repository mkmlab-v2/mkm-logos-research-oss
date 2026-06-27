/** Obsidian-style local graph BFS — lens context mesh hop index v1 */

export type HopNeighbor = {
  id: string;
  edge_type?: string;
  weight?: number;
};

export type HopIndexNode = {
  neighbors: HopNeighbor[];
};

export type LensContextMeshHopIndexDoc = {
  schema_version: string;
  lens_id?: string;
  stats?: { node_count?: number; undirected_edge_pairs?: number };
  nodes: Record<string, HopIndexNode>;
};

export function bfsVisibleNodeIds(
  hopIndex: LensContextMeshHopIndexDoc,
  seedIds: string[],
  depth: number,
  maxNodes: number,
): Set<string> {
  const nodes = hopIndex.nodes || {};
  const keys = Object.keys(nodes);
  if (!keys.length) return new Set();

  const maxD = Math.max(1, Math.min(8, Math.floor(depth)));
  const cap = Math.max(1, Math.floor(maxNodes));
  let seeds = seedIds.filter((id) => nodes[id]);
  if (!seeds.length) seeds = [keys[0]];

  const seen = new Set<string>();
  const order: string[] = [];
  const queue: Array<{ id: string; d: number }> = [];

  for (const s of seeds) {
    if (seen.has(s)) continue;
    seen.add(s);
    order.push(s);
    queue.push({ id: s, d: 0 });
  }

  while (queue.length && order.length < cap) {
    const { id, d } = queue.shift()!;
    if (d >= maxD) continue;
    const neighbors = nodes[id]?.neighbors || [];
    for (const nb of neighbors) {
      const nid = nb.id;
      if (!nid || seen.has(nid)) continue;
      seen.add(nid);
      order.push(nid);
      queue.push({ id: nid, d: d + 1 });
      if (order.length >= cap) break;
    }
  }
  return new Set(order);
}

export function filterGraphSliceDoc<T extends { nodes?: Array<{ id: string }>; edges?: Array<{ src: string; dst: string }> }>(
  doc: T,
  visible: Set<string>,
): T {
  const nodes = (doc.nodes || []).filter((n) => visible.has(n.id));
  const present = new Set(nodes.map((n) => n.id));
  const edges = (doc.edges || []).filter((e) => present.has(e.src) && present.has(e.dst));
  return { ...doc, nodes, edges };
}
