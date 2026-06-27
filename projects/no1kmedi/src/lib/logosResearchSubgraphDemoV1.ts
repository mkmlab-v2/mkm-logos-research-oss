export type SubgraphDemoBeat = {
  at_ms: number;
  kind: "start" | "spine_node" | "verse_ref" | "complete";
  nodeId?: string;
  ref?: string;
  label: string;
  progress: number;
};

export type SubgraphDemoLabels = {
  start: string;
  spine: string;
  verse: string;
  complete: string;
};

const DEFAULT_LABELS: SubgraphDemoLabels = {
  start: "경로 엔진 시동 · preset 로드",
  spine: "추론 spine 점등",
  verse: "citation lock · 구절 포커스",
  complete: "경로 시각화 완료 · [HYPO]",
};

/** ~3s entry demo: spine nodes light in order, then first verse ref, then complete. */
export function buildSubgraphEntryDemoTimeline(
  pathSpineIds: string[],
  verseRefs: string[],
  labels: Partial<SubgraphDemoLabels> = {},
): SubgraphDemoBeat[] {
  const L = { ...DEFAULT_LABELS, ...labels };
  const beats: SubgraphDemoBeat[] = [
    { at_ms: 0, kind: "start", label: L.start, progress: 10 },
  ];

  const spine = pathSpineIds.filter(Boolean);
  if (spine.length) {
    const span = spine.length === 1 ? 0 : Math.floor(1800 / (spine.length - 1));
    spine.forEach((nodeId, index) => {
      beats.push({
        at_ms: 400 + index * span,
        kind: "spine_node",
        nodeId,
        label: L.spine,
        progress: 22 + Math.floor((58 * (index + 1)) / spine.length),
      });
    });
  }

  const firstRef = verseRefs.find(Boolean);
  if (firstRef) {
    beats.push({
      at_ms: 2350,
      kind: "verse_ref",
      ref: firstRef,
      label: L.verse,
      progress: 88,
    });
  }

  beats.push({
    at_ms: 3000,
    kind: "complete",
    label: L.complete,
    progress: 100,
  });

  return beats;
}

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
