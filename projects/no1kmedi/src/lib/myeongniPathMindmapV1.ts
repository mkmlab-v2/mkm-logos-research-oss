/** Myeongni path mindmap model (B-track · mid-term direction · [HYPO] · NON_GATING). */

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

export const MYEONGNI_MINDMAP_LEAF_KINDS = ["ten_god", "oheng", "strength"] as const;

export type MyeongniMindmapNodeKind =
  | "root"
  | "pillar"
  | "luck"
  | "ten_god"
  | "oheng"
  | "strength";

export type MyeongniLiteMindmapInput = {
  query: string;
  pillars?: {
    year?: string | null;
    month?: string | null;
    day?: string | null;
    hour?: string | null;
  };
  daewoon_current?: {
    pillar?: string | null;
    age_start?: number | null;
    age_end?: number | null;
  } | null;
  sewoon_current?: {
    calendar_year?: number | null;
    pillar?: string | null;
  } | null;
  ten_god_lite?: {
    counts_combined_ko?: Record<string, number>;
  };
  oheng_visible?: {
    dominant_element_visible?: string | null;
    weakest_element_visible?: string | null;
  };
  strength_hint?: {
    strength_label?: string | null;
  };
};

export type { MindmapNode, MindmapEdge, PathMindmapModel, MindmapLayoutNode };
export {
  layoutPathMindmapRadial,
  mindmapNodeIdsForGraphPulse,
  curvedEdgePath,
};

const PILLAR_KEYS = [
  ["year", "년주"],
  ["month", "월주"],
  ["day", "일주"],
  ["hour", "시주"],
] as const;

const MAX_TEN_GODS = 4;

function topTenGods(counts?: Record<string, number>): Array<[string, number]> {
  if (!counts) return [];
  return Object.entries(counts)
    .filter(([, v]) => typeof v === "number" && v > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, MAX_TEN_GODS);
}

export function buildMyeongniPathMindmapModel(input: MyeongniLiteMindmapInput): PathMindmapModel {
  const rootId = "mn:root";
  const nodes: MindmapNode[] = [
    {
      id: rootId,
      label: truncateMindmapLabel(input.query || "명리 질의", 56),
      kind: "root",
      depth: 0,
    },
  ];
  const edges: MindmapEdge[] = [];

  const spine: Array<{ id: string; label: string; kind: MyeongniMindmapNodeKind; parentId: string }> =
    [];

  for (const [key, ko] of PILLAR_KEYS) {
    const pillar = input.pillars?.[key];
    if (!pillar) continue;
    const id = `mn:pillar:${key}`;
    spine.push({
      id,
      label: truncateMindmapLabel(`${ko} ${pillar}`, 28),
      kind: "pillar",
      parentId: rootId,
    });
  }

  const dae = input.daewoon_current;
  if (dae?.pillar) {
    const age =
      dae.age_start != null && dae.age_end != null
        ? ` (${dae.age_start}–${dae.age_end}세)`
        : "";
    spine.push({
      id: "mn:luck:daewoon",
      label: truncateMindmapLabel(`대운 ${dae.pillar}${age}`, 32),
      kind: "luck",
      parentId: rootId,
    });
  }

  const sew = input.sewoon_current;
  if (sew?.pillar) {
    const yr = sew.calendar_year != null ? `${sew.calendar_year} ` : "";
    spine.push({
      id: "mn:luck:sewoon",
      label: truncateMindmapLabel(`세운 ${yr}${sew.pillar}`, 32),
      kind: "luck",
      parentId: rootId,
    });
  }

  for (const s of spine) {
    nodes.push({
      id: s.id,
      label: s.label,
      kind: s.kind,
      depth: 1,
      parentId: s.parentId,
    });
    edges.push({ from: s.parentId, to: s.id });
  }

  const dayParent = spine.find((s) => s.id === "mn:pillar:day")?.id || rootId;

  for (const [name, count] of topTenGods(input.ten_god_lite?.counts_combined_ko)) {
    const id = `mn:tg:${name}`;
    nodes.push({
      id,
      label: truncateMindmapLabel(`${name}×${count}`, 22),
      kind: "ten_god",
      depth: 2,
      parentId: dayParent,
      meta: name,
    });
    edges.push({ from: dayParent, to: id });
  }

  const dom = input.oheng_visible?.dominant_element_visible;
  const weak = input.oheng_visible?.weakest_element_visible;
  if (dom || weak) {
    const parts = [dom ? `旺${dom}` : "", weak ? `弱${weak}` : ""].filter(Boolean).join(" · ");
    const id = "mn:oheng:profile";
    nodes.push({
      id,
      label: truncateMindmapLabel(parts, 24),
      kind: "oheng",
      depth: 2,
      parentId: rootId,
    });
    edges.push({ from: rootId, to: id });
  }

  const strength = input.strength_hint?.strength_label;
  if (strength) {
    const id = "mn:strength:hint";
    nodes.push({
      id,
      label: truncateMindmapLabel(strength, 24),
      kind: "strength",
      depth: 2,
      parentId: dayParent,
    });
    edges.push({ from: dayParent, to: id });
  }

  return { nodes, edges, rootId };
}

export function layoutMyeongniPathMindmapRadial(
  model: PathMindmapModel,
  width: number,
  height: number,
  presetId?: string,
): MindmapLayoutNode[] {
  return layoutPathMindmapRadial(model, width, height, {
    leafKinds: [...MYEONGNI_MINDMAP_LEAF_KINDS],
    presetId,
  });
}

export function mindmapNodeIdsForMyeongniFocus(focus: string, model: PathMindmapModel): string[] {
  return mindmapNodeIdsForLabelMatch(focus, model);
}
