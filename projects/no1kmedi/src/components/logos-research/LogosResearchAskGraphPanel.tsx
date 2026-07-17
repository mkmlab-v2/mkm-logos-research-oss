"use client";

import { useEffect, useMemo, useState } from "react";

import { LogosResearchPathMindmapPanel } from "@/components/logos-research/LogosResearchPathMindmapPanel";
import {
  buildAskGraphMeshSummary,
  buildAskGraphNodeTooltips,
  collectAskGraphSeedRefs,
  exceedsAskGraphRenderBudget,
  filterPathMindmapForVizMode,
  isLogosAskGraphV1Enabled,
  LOGOS_ASK_GRAPH_PULSE_DEBOUNCE_MS,
  LOGOS_ASK_GRAPH_MAX_VERSE_REFS,
  resolveAskGraphSeedIds,
  shouldPulseAskGraph,
  type AskGraphStreamPhase,
  type AskGraphVizMode,
} from "@/lib/logosAskGraphSidecarV1";
import { buildPathMindmapModel } from "@/lib/logosResearchPathMindmapV1";
import { buildMindmapMeshSummary } from "@/lib/logosResearchPathMindmapMeshV1";
import { prefersReducedMotion } from "@/lib/logosResearchSubgraphDemoV1";
import { useLogosStudioGraphSlice } from "@/lib/useLogosStudioGraphSliceV1";

type Props = {
  query: string;
  verseRefs: string[];
  citationLockAnchors?: string[];
  presetId?: string | null;
  streamPhase?: AskGraphStreamPhase;
  height?: number;
  braidFocusRef?: string | null;
  onBraidFocusRef?: (ref: string) => void;
};

export function LogosResearchAskGraphPanel({
  query,
  verseRefs,
  citationLockAnchors = [],
  presetId = null,
  streamPhase = "idle",
  height = 420,
  braidFocusRef = null,
  onBraidFocusRef,
}: Props) {
  const enabled = isLogosAskGraphV1Enabled();
  const boundedRefs = useMemo(
    () => verseRefs.filter(Boolean).slice(0, LOGOS_ASK_GRAPH_MAX_VERSE_REFS),
    [verseRefs],
  );
  const seedRefs = useMemo(
    () => collectAskGraphSeedRefs(boundedRefs, citationLockAnchors),
    [boundedRefs, citationLockAnchors],
  );
  const [mountGraph, setMountGraph] = useState(false);
  const [vizMode, setVizMode] = useState<AskGraphVizMode>("path");

  useEffect(() => {
    if (!enabled || !seedRefs.length) {
      setMountGraph(false);
      return;
    }
    if (streamPhase === "snapshot" || streamPhase === "done") {
      setMountGraph(true);
      return;
    }
    if (streamPhase === "s4" && mountGraph) return;
    const t = window.setTimeout(() => setMountGraph(true), LOGOS_ASK_GRAPH_PULSE_DEBOUNCE_MS);
    return () => window.clearTimeout(t);
  }, [enabled, mountGraph, seedRefs.length, streamPhase]);

  const { graphDoc, hopIndex, loadError, loading } = useLogosStudioGraphSlice(enabled && mountGraph);

  const seedIds = useMemo(
    () => resolveAskGraphSeedIds(seedRefs, graphDoc),
    [graphDoc, seedRefs],
  );

  const meshSummary = useMemo(
    () => buildAskGraphMeshSummary(graphDoc, hopIndex, seedIds),
    [graphDoc, hopIndex, seedIds],
  );

  const rawModel = useMemo(() => {
    const base = buildPathMindmapModel({ query: query || "연구 질의", verseRefs: boundedRefs });
    if (!meshSummary) return base;
    return buildMindmapMeshSummary({
      base,
      graphDoc: meshSummary.graphDoc,
      hopIndex: meshSummary.hopIndex,
      seedIds: meshSummary.seedIds,
      nodeById: meshSummary.nodeById,
      maxMesh: 12,
    }).model;
  }, [boundedRefs, meshSummary, query]);

  const overBudget = exceedsAskGraphRenderBudget(rawModel.nodes.length);
  const effectiveVizMode: AskGraphVizMode = overBudget ? "path" : vizMode;

  const previewModel = useMemo(
    () => filterPathMindmapForVizMode(rawModel, effectiveVizMode),
    [rawModel, effectiveVizMode],
  );

  const nodeTooltips = useMemo(
    () =>
      buildAskGraphNodeTooltips(
        previewModel,
        boundedRefs,
        citationLockAnchors,
        meshSummary?.nodeById ?? {},
      ),
    [previewModel, boundedRefs, citationLockAnchors, meshSummary?.nodeById],
  );

  const pulse = shouldPulseAskGraph(streamPhase) && !prefersReducedMotion();
  const pulseGraphNodeIds = pulse ? seedIds : [];
  const pulseVerseRef = braidFocusRef || (pulse && boundedRefs[0] ? boundedRefs[0] : null);
  const graphLoading = mountGraph && loading;
  const meshUnresolved = mountGraph && !loading && Boolean(graphDoc) && seedIds.length === 0;

  if (!enabled || !boundedRefs.length) return null;

  const showSkeleton = !mountGraph || graphLoading;

  return (
    <aside
      className="lr-ask-graph-panel"
      data-logos-ask-graph="1"
      data-logos-ask-graph-phase={streamPhase}
      data-logos-ask-graph-viz={effectiveVizMode}
      aria-label="의미 연결망 (Citation lock 기반)"
    >
      <div className="lr-ask-graph-panel-head">
        <p className="lr-ask-graph-panel-label">의미 연결망 · 연구 참고</p>
        {mountGraph ? (
          <div className="lr-ask-graph-viz-toggle" role="group" aria-label="시각화 모드">
            <button
              type="button"
              className={`lr-ask-graph-viz-btn${effectiveVizMode === "path" ? " lr-ask-graph-viz-btn--active" : ""}`}
              disabled={overBudget}
              aria-pressed={effectiveVizMode === "path"}
              onClick={() => setVizMode("path")}
            >
              경로
            </button>
            <button
              type="button"
              className={`lr-ask-graph-viz-btn${effectiveVizMode === "full" ? " lr-ask-graph-viz-btn--active" : ""}`}
              disabled={overBudget}
              aria-pressed={effectiveVizMode === "full"}
              onClick={() => setVizMode("full")}
            >
              연결망
            </button>
          </div>
        ) : null}
      </div>
      {overBudget ? (
        <p className="lr-ask-muted lr-ask-graph-panel-budget">
          노드 {previewModel.nodes.length}개 — 성능 가드로 경로 포커스만 표시합니다.
        </p>
      ) : null}
      {loadError && mountGraph && !graphLoading ? (
        <p className="lr-ask-muted lr-ask-graph-panel-error">
          연결망 요약을 불러오지 못했습니다. 구절 경로만 표시합니다.
        </p>
      ) : null}
      {meshUnresolved ? (
        <p className="lr-ask-muted lr-ask-graph-panel-empty">
          슬라이스에 매칭 노드가 없어 경로(spine) 뷰만 표시합니다.
        </p>
      ) : null}
      {showSkeleton ? (
        <div
          className="lr-ask-graph-skeleton"
          role="status"
          aria-label={mountGraph ? "연결망 불러오는 중" : "Citation lock 준비 중"}
        >
          <div className="lr-ask-graph-skeleton-orbit" aria-hidden="true" />
          <p className="lr-ask-muted lr-ask-graph-panel-loading">
            {mountGraph ? "연결망 슬라이스 불러오는 중…" : "Citation lock 준비 중…"}
          </p>
        </div>
      ) : (
        <LogosResearchPathMindmapPanel
          query={query || "연구 질의"}
          presetId={presetId ?? ""}
          verseRefs={boundedRefs}
          meshSummary={meshSummary ?? undefined}
          pulseGraphNodeIds={pulseGraphNodeIds}
          pulseVerseRef={pulseVerseRef}
          height={height}
          compactMeta
          vizMode={effectiveVizMode}
          nodeTooltips={nodeTooltips}
          onVerseClick={onBraidFocusRef}
        />
      )}
    </aside>
  );
}
