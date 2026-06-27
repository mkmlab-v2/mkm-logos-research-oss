export type LogosReasoningPathV1 = {
  schema_version?: string;
  node_ids?: string[];
  path_label_ko?: string;
};

export type LogosRouterPathV1 = {
  query?: string;
  note_ko?: string;
  path_steps?: string[];
  verse_refs?: string[];
  bridges_matched?: number;
  node_ids?: string[];
  path_id?: string;
  reasoning_path_v1?: LogosReasoningPathV1;
};

export type LogosHighlightPreset = {
  highlight_node_ids?: string[];
  reasoning_path_v1?: LogosReasoningPathV1;
  router_path_v1?: LogosRouterPathV1;
};

export type LogosGraphSliceNode = {
  id: string;
  kind?: string;
  label?: string;
  ref?: string;
  hub_score?: number;
};

export function normalizeRefKey(ref: string): string {
  return String(ref || "")
    .trim()
    .replace(/\s+/g, "");
}

export function buildRefToNodeIndex(nodes: LogosGraphSliceNode[]): Record<string, string[]> {
  const refToNodeIds: Record<string, string[]> = {};
  for (const node of nodes) {
    const ref = normalizeRefKey(node.ref || node.label || "");
    if (ref) {
      refToNodeIds[ref] = refToNodeIds[ref] || [];
      if (!refToNodeIds[ref].includes(node.id)) refToNodeIds[ref].push(node.id);
    }
    const tail = String(node.id || "").split("::").pop();
    if (tail && tail.includes(".")) {
      refToNodeIds[tail] = refToNodeIds[tail] || [];
      if (!refToNodeIds[tail].includes(node.id)) refToNodeIds[tail].push(node.id);
    }
  }
  return refToNodeIds;
}

export function nodeIdsForRef(
  ref: string,
  refToNodeIds: Record<string, string[]>,
): string[] {
  const key = normalizeRefKey(ref);
  if (refToNodeIds[key]?.length) return refToNodeIds[key];
  const book = key.replace(/\./g, "");
  const hits: string[] = [];
  for (const k of Object.keys(refToNodeIds)) {
    if (k.replace(/\./g, "").toLowerCase() === book.toLowerCase()) {
      for (const id of refToNodeIds[k]) {
        if (!hits.includes(id)) hits.push(id);
      }
    }
  }
  return hits;
}

export function resolveRefsToIds(
  refs: string[],
  refToNodeIds: Record<string, string[]>,
): string[] {
  const ids: string[] = [];
  for (const ref of refs) {
    for (const id of nodeIdsForRef(ref, refToNodeIds)) {
      if (!ids.includes(id)) ids.push(id);
    }
  }
  return ids;
}

/** Parity with showroom `highlightIdsForPreset` — router node_ids first. */
export function resolveHighlightNodeIds(
  preset: LogosHighlightPreset | null | undefined,
  refToNodeIds?: Record<string, string[]>,
): string[] {
  if (!preset) return [];
  const rp = preset.router_path_v1;
  if (rp?.node_ids?.length) return rp.node_ids;

  if (rp?.verse_refs?.length && refToNodeIds) {
    const fromRefs = resolveRefsToIds(rp.verse_refs, refToNodeIds);
    if (fromRefs.length) return fromRefs;
  }

  const reasoning =
    rp?.reasoning_path_v1 ?? preset.reasoning_path_v1;
  if (reasoning?.node_ids && reasoning.node_ids.length >= 2) {
    return reasoning.node_ids;
  }

  if (preset.highlight_node_ids?.length) return preset.highlight_node_ids;
  return [];
}

export function nodeLabelFromSlice(
  nodeId: string,
  nodeById: Record<string, LogosGraphSliceNode>,
): string {
  const node = nodeById[nodeId];
  if (!node) return String(nodeId).split("::").pop() || nodeId;
  return node.label || node.ref || String(nodeId).split("::").pop() || nodeId;
}
