/** Path mindmap model (Logos Studio · research_only · [HYPO]). */

import { formatPathStepHuman } from "@/lib/logosResearchStudioDisplayV1";
import {
  layoutPathMindmapRadial,
  mindmapNodeIdsForGraphPulse,
  mindmapNodeIdsForLabelMatch,
  truncateMindmapLabel,
  curvedEdgePath,
  type MindmapEdge,
  type MindmapLayoutNode,
  type MindmapNode,
  type PathMindmapModel,
} from "@/lib/pathMindmapCoreV1";

export type MindmapNodeKind = "root" | "spine" | "verse" | "step";

export type { MindmapNode, MindmapEdge, PathMindmapModel, MindmapLayoutNode };
export {
  layoutPathMindmapRadial,
  mindmapNodeIdsForGraphPulse,
  curvedEdgePath,
};

const MAX_SPINE = 6;
const MAX_VERSES = 10;

export type BuildPathMindmapInput = {
  query: string;
  pathSteps?: string[];
  verseRefs: string[];
  spineItems?: Array<{ id: string; label: string }>;
};

export function buildPathMindmapModel(input: BuildPathMindmapInput): PathMindmapModel {
  const rootId = "mm:root";
  const nodes: MindmapNode[] = [
    {
      id: rootId,
      label: truncateMindmapLabel(input.query || "질의", 56),
      kind: "root",
      depth: 0,
    },
  ];
  const edges: MindmapEdge[] = [];

  const spineItems: Array<{ id: string; label: string; graphNodeId?: string }> = [];
  if (input.spineItems?.length) {
    for (const s of input.spineItems.slice(0, MAX_SPINE)) {
      spineItems.push({
        id: `mm:spine:${s.id}`,
        label: truncateMindmapLabel(s.label, 40),
        graphNodeId: s.id,
      });
    }
  } else if (input.pathSteps?.length) {
    input.pathSteps.slice(0, MAX_SPINE).forEach((step, i) => {
      spineItems.push({
        id: `mm:step:${i}`,
        label: truncateMindmapLabel(formatPathStepHuman(step), 40),
      });
    });
  }

  for (const s of spineItems) {
    nodes.push({
      id: s.id,
      label: s.label,
      kind: input.spineItems?.length ? "spine" : "step",
      depth: 1,
      parentId: rootId,
      graphNodeId: s.graphNodeId,
    });
    edges.push({ from: rootId, to: s.id });
  }

  const verses = input.verseRefs.filter(Boolean).slice(0, MAX_VERSES);
  const parents = spineItems.length ? spineItems : [{ id: rootId, label: "" }];
  verses.forEach((ref, i) => {
    const parent = spineItems.length ? spineItems[i % spineItems.length] : parents[0];
    const vid = `mm:verse:${ref.replace(/\s+/g, "")}`;
    nodes.push({
      id: vid,
      label: ref,
      kind: "verse",
      depth: spineItems.length ? 2 : 1,
      parentId: parent.id,
    });
    edges.push({ from: parent.id, to: vid });
  });

  return { nodes, edges, rootId };
}

export function mindmapNodeIdsForVerseRef(ref: string, model: PathMindmapModel): string[] {
  return mindmapNodeIdsForLabelMatch(ref, model);
}
