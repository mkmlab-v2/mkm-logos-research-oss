/** Myeongni mindmap entry demo timeline (~3s · research_only). */

import type { PathMindmapModel } from "@/lib/pathMindmapCoreV1";

export type MyeongniDemoBeat = {
  at_ms: number;
  kind: "start" | "pillar" | "luck" | "leaf" | "complete";
  nodeId?: string;
  label: string;
  progress: number;
};

export function buildMyeongniMindmapDemoTimeline(model: PathMindmapModel): MyeongniDemoBeat[] {
  const beats: MyeongniDemoBeat[] = [
    { at_ms: 0, kind: "start", label: "명리 lite 로드 · 四柱 spine", progress: 8 },
  ];

  const pillars = model.nodes.filter((n) => n.kind === "pillar");
  const luck = model.nodes.filter((n) => n.kind === "luck");
  const leaves = model.nodes.filter((n) =>
    ["ten_god", "oheng", "strength"].includes(n.kind),
  );

  pillars.forEach((node, i) => {
    beats.push({
      at_ms: 350 + i * 380,
      kind: "pillar",
      nodeId: node.id,
      label: node.label,
      progress: 18 + Math.floor((35 * (i + 1)) / Math.max(pillars.length, 1)),
    });
  });

  luck.forEach((node, i) => {
    beats.push({
      at_ms: 1700 + i * 420,
      kind: "luck",
      nodeId: node.id,
      label: node.label,
      progress: 55 + i * 12,
    });
  });

  const firstLeaf = leaves[0];
  if (firstLeaf) {
    beats.push({
      at_ms: 2550,
      kind: "leaf",
      nodeId: firstLeaf.id,
      label: "십성·오행 leaf",
      progress: 88,
    });
  }

  beats.push({
    at_ms: 3000,
    kind: "complete",
    label: "경로 시각화 완료 · [HYPO] NON_GATING",
    progress: 100,
  });

  return beats;
}

export function activeNodeIdAtBeat(
  beats: MyeongniDemoBeat[],
  elapsedMs: number,
): string | null {
  let last: string | null = null;
  for (const b of beats) {
    if (b.at_ms > elapsedMs) break;
    if (b.nodeId) last = b.nodeId;
  }
  return last;
}
