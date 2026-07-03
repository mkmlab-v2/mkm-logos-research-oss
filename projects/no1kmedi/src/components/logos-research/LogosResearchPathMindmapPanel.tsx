"use client";

import { useMemo } from "react";

import { PathMindmapSvgPanel } from "@/components/path-mindmap/PathMindmapSvgPanel";
import type { LensContextMeshHopIndexDoc } from "@/lib/lensContextMeshBfsV1";
import type { LogosGraphSliceDoc } from "@/lib/logosResearchGraphTypesV1";
import type { LogosGraphSliceNode } from "@/lib/logosResearchHighlightV1";
import {
  buildPathMindmapModel,
  layoutPathMindmapRadial,
  mindmapNodeIdsForGraphPulse,
  mindmapNodeIdsForVerseRef,
} from "@/lib/logosResearchPathMindmapV1";
import { buildMindmapMeshSummary } from "@/lib/logosResearchPathMindmapMeshV1";
import {
  filterPathMindmapForVizMode,
  type AskGraphVizMode,
} from "@/lib/logosAskGraphSidecarV1";

type Props = {
  query: string;
  presetId: string;
  pathSteps?: string[];
  verseRefs: string[];
  spineItems?: Array<{ id: string; label: string }>;
  meshSummary?: {
    graphDoc: LogosGraphSliceDoc | null;
    hopIndex: LensContextMeshHopIndexDoc | null;
    seedIds: string[];
    nodeById?: Record<string, LogosGraphSliceNode>;
  };
  pulseGraphNodeIds?: string[];
  pulseVerseRef?: string | null;
  demoProgress?: number;
  demoLabel?: string;
  demoRunning?: boolean;
  height?: number;
  compactMeta?: boolean;
  vizMode?: AskGraphVizMode;
  nodeTooltips?: Record<string, string>;
  onVerseClick?: (ref: string) => void;
  onReplayDemo?: () => void;
};

const KIND_STYLES = {
  root: { fill: "#1c1917", stroke: "#2d7a68", text: "#ffffff", r: 36 },
  spine: { fill: "#ecfdf5", stroke: "#2d7a68", text: "#1c1917", r: 20 },
  step: { fill: "#f5f0e8", stroke: "#b45309", text: "#292524", r: 18 },
  verse: { fill: "#fffbeb", stroke: "#d97706", text: "#78350f", r: 16 },
  mesh: { fill: "rgba(148,163,184,0.32)", stroke: "rgba(100,116,139,0.65)", text: "#64748b", r: 5 },
};

export function LogosResearchPathMindmapPanel({
  query,
  presetId,
  pathSteps,
  verseRefs,
  spineItems,
  meshSummary,
  pulseGraphNodeIds = [],
  pulseVerseRef,
  demoProgress = 0,
  demoLabel,
  demoRunning = false,
  height = 480,
  compactMeta = false,
  vizMode = "full",
  nodeTooltips,
  onVerseClick,
  onReplayDemo,
}: Props) {
  const baseModel = useMemo(
    () =>
      buildPathMindmapModel({
        query,
        pathSteps,
        verseRefs,
        spineItems,
      }),
    [pathSteps, query, spineItems, verseRefs],
  );

  const { model: rawModel, meshShown, meshTotal } = useMemo(() => {
    if (!meshSummary?.graphDoc || !meshSummary.hopIndex || !meshSummary.seedIds.length) {
      return { model: baseModel, meshShown: 0, meshTotal: meshSummary?.graphDoc?.nodes?.length ?? 0 };
    }
    return buildMindmapMeshSummary({
      base: baseModel,
      graphDoc: meshSummary.graphDoc,
      hopIndex: meshSummary.hopIndex,
      seedIds: meshSummary.seedIds,
      nodeById: meshSummary.nodeById,
      maxMesh: compactMeta ? 12 : undefined,
    });
  }, [baseModel, meshSummary]);

  const model = useMemo(
    () => filterPathMindmapForVizMode(rawModel, vizMode),
    [rawModel, vizMode],
  );

  const layoutFn = useMemo(
    () => (m: typeof model, w: number, h: number) =>
      layoutPathMindmapRadial(m, w, h, { presetId, leafKinds: ["verse"] }),
    [presetId],
  );

  const activeIds = useMemo(() => {
    const ids = new Set<string>();
    for (const id of mindmapNodeIdsForGraphPulse(pulseGraphNodeIds, model)) ids.add(id);
    if (pulseVerseRef) {
      for (const id of mindmapNodeIdsForVerseRef(pulseVerseRef, model)) ids.add(id);
    }
    return ids;
  }, [model, pulseGraphNodeIds, pulseVerseRef]);

  const pathNodeCount = baseModel.nodes.length;
  const meta = compactMeta
    ? vizMode === "path"
      ? `경로 포커스 · ${pathNodeCount}노드`
      : meshShown
        ? `경로 ${pathNodeCount} · 연결 ${meshShown}/${meshTotal || meshShown}`
        : "질의 · spine · 구절"
    : vizMode === "path"
      ? `경로 포커스 · ${pathNodeCount}노드 · [NON_GATING]`
      : meshShown
        ? `경로 ${pathNodeCount} · mesh ${meshShown}/${meshTotal || meshShown} · [HYPO]`
        : "질의 중심 · spine · 구절 가지 · [HYPO] research_only";

  const footnote = compactMeta
    ? vizMode === "path"
      ? "경로 포커스 — 구절을 눌러 출처를 확인하세요"
      : meshShown
        ? "밝은 노드=경로 · 흐린 점=연결 요약"
        : "구절 hover → 출처 확인"
    : vizMode === "path"
      ? "경로 포커스 — mesh 숨김 · 구절 hover → citation lock"
      : meshShown
        ? "밝은 노드=경로 · 흐린 점=mesh 요약 · hover → citation lock"
        : "구절 hover → citation lock · research_only";

  return (
    <PathMindmapSvgPanel
      model={model}
      layoutFn={layoutFn}
      kindStyles={KIND_STYLES}
      activeIds={activeIds}
      nodeTooltips={nodeTooltips}
      title="경로 마인드맵"
      meta={meta}
      footnote={footnote}
      svgTitle="Logos 경로 마인드맵"
      height={height}
      panelDataAttributes={{
        "data-logos-path-mindmap": "1",
        "data-logos-viz-mode": vizMode,
        ...(meshShown ? { "data-logos-mindmap-mesh-count": String(meshShown) } : {}),
      }}
      gradientId="lr-mm-bg-glow"
      leafKinds={["verse"]}
      onLeafClick={onVerseClick ? (n) => onVerseClick(n.label) : undefined}
      demoProgress={demoProgress}
      demoLabel={demoLabel}
      demoRunning={demoRunning}
      onReplayDemo={onReplayDemo}
      externalRootCaption={compactMeta ? query : undefined}
    />
  );
}
