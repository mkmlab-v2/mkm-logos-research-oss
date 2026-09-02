/**
 * Ask / path-mindmap edge relation taxonomy (D-VIZ-2).
 * Honest minimal types from builder provenance — no gematria-match without payload.
 * research_only · [HYPO] · [NON_GATING] · send_gate HOLD
 */

import type { MindmapEdge, MindmapNode, PathMindmapModel } from "@/lib/pathMindmapCoreV1";

/** Fixed enum — do not invent gematria_match / lemma without data. */
export const ASK_GRAPH_EDGE_RELATIONS = [
  "path_sequential",
  "citation",
  "related",
] as const;

export type AskGraphEdgeRelation = (typeof ASK_GRAPH_EDGE_RELATIONS)[number];

export const ASK_GRAPH_EDGE_LABEL_KO: Record<AskGraphEdgeRelation, string> = {
  path_sequential: "경로",
  citation: "인용",
  related: "연결",
};

export const ASK_GRAPH_EDGE_LABEL_SHORT: Record<AskGraphEdgeRelation, string> = {
  path_sequential: "경로",
  citation: "인용",
  related: "연결",
};

export const ASK_GRAPH_EDGE_CSS: Record<AskGraphEdgeRelation, string> = {
  path_sequential: "lr-studio-mindmap-edge--path",
  citation: "lr-studio-mindmap-edge--citation",
  related: "lr-studio-mindmap-edge--related",
};

export function isAskGraphEdgeRelation(raw: unknown): raw is AskGraphEdgeRelation {
  return (
    typeof raw === "string" &&
    (ASK_GRAPH_EDGE_RELATIONS as readonly string[]).includes(raw)
  );
}

/**
 * Resolve edge type: prefer explicit `relation`; else infer from endpoint kinds
 * (legacy edges without tags). Mesh involvement → related; verse leaf → citation;
 * else path_sequential. Never claims gematria-match.
 */
export function resolveAskGraphEdgeRelation(
  edge: MindmapEdge,
  nodeById: Map<string, MindmapNode> | Record<string, MindmapNode>,
): AskGraphEdgeRelation {
  if (isAskGraphEdgeRelation(edge.relation)) return edge.relation;

  const get = (id: string): MindmapNode | undefined =>
    nodeById instanceof Map ? nodeById.get(id) : nodeById[id];
  const a = get(edge.from);
  const b = get(edge.to);
  if (a?.kind === "mesh" || b?.kind === "mesh") return "related";
  if (a?.kind === "verse" || b?.kind === "verse") return "citation";
  return "path_sequential";
}

export function edgeRelationCssClass(relation: AskGraphEdgeRelation): string {
  return ASK_GRAPH_EDGE_CSS[relation];
}

export function summarizeEdgeRelations(model: PathMindmapModel): Record<AskGraphEdgeRelation, number> {
  const nodeById = new Map(model.nodes.map((n) => [n.id, n]));
  const counts: Record<AskGraphEdgeRelation, number> = {
    path_sequential: 0,
    citation: 0,
    related: 0,
  };
  for (const e of model.edges) {
    counts[resolveAskGraphEdgeRelation(e, nodeById)] += 1;
  }
  return counts;
}

export function presentEdgeRelationTypes(model: PathMindmapModel): AskGraphEdgeRelation[] {
  const counts = summarizeEdgeRelations(model);
  return ASK_GRAPH_EDGE_RELATIONS.filter((r) => counts[r] > 0);
}
