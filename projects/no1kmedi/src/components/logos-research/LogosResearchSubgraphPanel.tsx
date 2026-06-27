"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { LogosResearchCitationSidecarPanel } from "@/components/logos-research/LogosResearchCitationSidecarPanel";
import { LogosResearchExploreMeshPanel } from "@/components/logos-research/LogosResearchExploreMeshPanel";
import { LogosResearchPathMindmapPanel } from "@/components/logos-research/LogosResearchPathMindmapPanel";
import { LogosResearchStoryboardPanel } from "@/components/logos-research/LogosResearchStoryboardPanel";
import { logosResearchCopy } from "@/content/logosResearchCopy";
import type { ConflictContextResult } from "@/lib/logosStudioConflictBridgeV1";
import {
  augmentGraphNodesWithRouterStubs,
  computeGraphSliceCoverage,
} from "@/lib/logosStudioGraphCoverageV1";
import { KIND_COLOR, type LogosGraphSliceDoc } from "@/lib/logosResearchGraphTypesV1";
import {
  buildRefToNodeIndex,
  nodeIdsForRef,
  nodeLabelFromSlice,
  type LogosGraphSliceNode,
} from "@/lib/logosResearchHighlightV1";
import {
  buildCitationDetail,
  type CitationSelection,
} from "@/lib/logosResearchCitationDetailV1";
import {
  bloomCoverageLabelKo,
  bloomSecondaryVerseRefsForRef,
} from "@/lib/logosStudioBloomSecondaryFetchV1";
import {
  lookupVerseCitationShard,
  useLogosVerseCitationShard,
} from "@/lib/logosResearchVerseCitationShardV1";
import {
  buildSubgraphEntryDemoTimeline,
  prefersReducedMotion,
  type SubgraphDemoBeat,
} from "@/lib/logosResearchSubgraphDemoV1";
import {
  bfsVisibleNodeIds,
  filterGraphSliceDoc,
} from "@/lib/lensContextMeshBfsV1";
import { useLogosStudioGraphSlice } from "@/lib/useLogosStudioGraphSliceV1";

const GRAPH_SLICE_URL = "/data/logos_studio/graph_slice_v1.json";
const HOP_INDEX_URL = "/data/logos_studio/context_mesh_hop_index_v1.json";
const MESH_DEFAULT_DEPTH = 2;
const MESH_MAX_DEPTH = 4;
const MESH_MAX_FOCUS_NODES = 40;

const GRAPH_LEGEND = [
  { id: "verse", label: "구절", color: KIND_COLOR.verse },
  { id: "theme", label: "테마 · spine", color: KIND_COLOR.theme },
  { id: "regime", label: "레짐", color: KIND_COLOR.regime },
  { id: "dim", label: "맥락 망", color: "rgba(148,163,184,0.35)" },
] as const;

export type StudioSubgraphResult = {
  preset_id: string;
  query?: string;
  answer?: string;
  query_mode?: string;
  highlight_node_ids: string[];
  path: {
    note_ko?: string | null;
    steps?: string[];
    verse_refs: string[];
    node_ids?: string[];
    bridges_matched?: number | null;
    reasoning_path_v1?: { node_ids?: string[]; path_label_ko?: string };
  };
  synthesis_meta?: {
    synthesis_mode?: string;
    llm_invoked?: boolean;
  } | null;
  conflict_context?: Extract<ConflictContextResult, { ok: true }> | null;
  graphrag_meta?: {
    bridges_matched?: number;
    paths_count?: number;
  };
  evidence_confidence?: {
    ecs_v1?: number;
    band?: "low" | "mid" | "high";
    components?: {
      path_depth_ratio?: number;
      cited_refs_strength?: number;
      conflict_entropy_penalty?: number;
    };
    note_ko?: string;
  } | null;
  insight_card?: {
    gap_ko?: string;
    one_liner_ko?: string;
    governance?: string;
  } | null;
};

import type { CitationDetailV1 } from "@/lib/logosResearchCitationDetailV1";

export type LogosSubgraphCitationSlotPayload = {
  detail: CitationDetailV1;
  onOpenExplore: () => void;
  onClear: () => void;
};

type Props = {
  result: StudioSubgraphResult;
  autoDemoOnMount?: boolean;
  productDemoMode?: boolean;
  /** canvas 모드: citation을 부모 citation dock으로 위임 */
  citationPlacement?: "inline" | "external";
  onCitationSlotChange?: (payload: LogosSubgraphCitationSlotPayload | null) => void;
  /** Antigravity scriptorium mockup — storyboard-first, chips on inquiry panel */
  scriptoriumMode?: boolean;
};

export function LogosResearchSubgraphPanel({
  result,
  autoDemoOnMount = false,
  productDemoMode = false,
  citationPlacement = "inline",
  onCitationSlotChange,
  scriptoriumMode = false,
}: Props) {
  const studio = "studio" in logosResearchCopy ? logosResearchCopy.studio : null;
  const sg = studio && "subgraph" in studio ? studio.subgraph : null;
  const { graphDoc, hopIndex, loadError } = useLogosStudioGraphSlice(true);
  const { shardDoc } = useLogosVerseCitationShard(true);
  const [meshDepth, setMeshDepth] = useState(MESH_DEFAULT_DEPTH);
  const [meshFocusId, setMeshFocusId] = useState<string | null>(null);
  const [pulseIds, setPulseIds] = useState<string[]>([]);
  const [focusBar, setFocusBar] = useState<string | null>(null);
  const [focusMode, setFocusMode] = useState<"ok" | "warn">("ok");
  const [autoFocusOn, setAutoFocusOn] = useState(false);
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoProgress, setDemoProgress] = useState(0);
  const [demoLabel, setDemoLabel] = useState("");
  const [activeView, setActiveView] = useState<"storyboard" | "mindmap" | "explore">(
    productDemoMode || scriptoriumMode ? "storyboard" : "mindmap",
  );
  const [pulseVerseRef, setPulseVerseRef] = useState<string | null>(null);
  const [citationSelection, setCitationSelection] = useState<CitationSelection | null>(null);
  const demoTimersRef = useRef<number[]>([]);
  const demoTokenRef = useRef(0);
  const autoDemoRanRef = useRef(false);

  const coverageNodes = useMemo(
    () => augmentGraphNodesWithRouterStubs(graphDoc?.nodes ?? [], hopIndex, result.path.verse_refs),
    [graphDoc, hopIndex, result.path.verse_refs],
  );

  const nodeById = useMemo(() => {
    const map: Record<string, LogosGraphSliceNode> = {};
    for (const n of coverageNodes) map[n.id] = n;
    return map;
  }, [coverageNodes]);

  const refToNodeIds = useMemo(
    () => buildRefToNodeIndex(coverageNodes),
    [coverageNodes],
  );

  const highlightIds = result.highlight_node_ids;
  const reasoningIds = result.path.reasoning_path_v1?.node_ids || [];
  const pathSpineIds =
    reasoningIds.length >= 2
      ? reasoningIds
      : result.path.node_ids?.length
        ? result.path.node_ids
        : highlightIds;

  const sliceCoverage = useMemo(
    () => computeGraphSliceCoverage(coverageNodes, result.path.verse_refs, highlightIds),
    [coverageNodes, highlightIds, result.path.verse_refs],
  );

  const [bloomSecondaryHint, setBloomSecondaryHint] = useState("");

  useEffect(() => {
    const anchor =
      sliceCoverage.unmappedRefs[0] || result.path.verse_refs[0] || null;
    if (!anchor) {
      setBloomSecondaryHint("");
      return;
    }
    let cancelled = false;
    void bloomSecondaryVerseRefsForRef(anchor).then((refs) => {
      if (cancelled) return;
      const pathSet = new Set(result.path.verse_refs);
      const extra = refs.filter((r) => !pathSet.has(r)).length;
      setBloomSecondaryHint(bloomCoverageLabelKo(Math.min(extra, 24)));
    });
    return () => {
      cancelled = true;
    };
  }, [result.path.verse_refs, sliceCoverage.unmappedRefs]);

  const unmappedRefSet = useMemo(
    () => new Set(sliceCoverage.unmappedRefs),
    [sliceCoverage.unmappedRefs],
  );

  const activeGhostRef = useMemo(() => {
    if (citationSelection?.kind === "verse" && unmappedRefSet.has(citationSelection.ref)) {
      return citationSelection.ref;
    }
    if (pulseVerseRef && unmappedRefSet.has(pulseVerseRef)) return pulseVerseRef;
    return null;
  }, [citationSelection, pulseVerseRef, unmappedRefSet]);

  const isRefInSlice = useCallback(
    (ref: string) => !unmappedRefSet.has(ref),
    [unmappedRefSet],
  );

  const meshSeedIds = useMemo(() => {
    const seeds = new Set<string>();
    if (meshFocusId) seeds.add(meshFocusId);
    for (const id of pathSpineIds) if (id) seeds.add(id);
    for (const id of highlightIds.slice(0, 16)) if (id) seeds.add(id);
    for (const id of sliceCoverage.mappedNodeIds.slice(0, 8)) if (id) seeds.add(id);
    return [...seeds];
  }, [highlightIds, meshFocusId, pathSpineIds, sliceCoverage.mappedNodeIds]);

  const visibleGraphDoc = useMemo(() => {
    if (!graphDoc) return null;
    let visible: Set<string>;
    if (hopIndex && meshSeedIds.length) {
      visible = bfsVisibleNodeIds(hopIndex, meshSeedIds, meshDepth, MESH_MAX_FOCUS_NODES);
    } else {
      visible = new Set<string>();
    }
    for (const id of [...pathSpineIds, ...highlightIds, ...sliceCoverage.mappedNodeIds]) {
      if (graphDoc.nodes?.some((n) => n.id === id)) visible.add(id);
    }
    if (!visible.size && graphDoc.nodes?.length) {
      return graphDoc;
    }
    return filterGraphSliceDoc(graphDoc, visible);
  }, [
    graphDoc,
    hopIndex,
    meshDepth,
    meshSeedIds,
    pathSpineIds,
    highlightIds,
    sliceCoverage.mappedNodeIds,
  ]);

  const totalNodeCount = graphDoc?.nodes?.length ?? 0;
  const nodeCount = visibleGraphDoc?.nodes?.length ?? 0;
  const meshActive = Boolean(hopIndex && meshSeedIds.length);

  const demoLabels = useMemo(
    () => ({
      start: sg?.demo_start ?? "경로 엔진 시동 · preset 로드",
      spine: sg?.demo_spine ?? "추론 spine 점등",
      verse: sg?.demo_verse ?? "citation lock · 구절 포커스",
      complete: sg?.demo_complete ?? "경로 시각화 완료 · [HYPO]",
    }),
    [sg],
  );

  const focusPrefix = sg?.focus_prefix ?? "포커스 ·";
  const missingInSlice = sg?.missing_in_slice ?? "슬라이스 외 · reading pack·sidecar 해설만";
  const pathPrefix = sg?.path_prefix ?? "경로 ·";
  const highlightedSuffix = sg?.highlighted_suffix ?? "개 노드 강조";

  const clearDemoTimers = useCallback(() => {
    for (const id of demoTimersRef.current) window.clearTimeout(id);
    demoTimersRef.current = [];
  }, []);

  const stopDemo = useCallback(() => {
    demoTokenRef.current += 1;
    clearDemoTimers();
    setDemoRunning(false);
  }, [clearDemoTimers]);

  const runDemoBeat = useCallback(
    (beat: SubgraphDemoBeat) => {
      setDemoProgress(beat.progress);
      setDemoLabel(beat.label);

      if (beat.kind === "spine_node" && beat.nodeId) {
        const label = nodeLabelFromSlice(beat.nodeId, nodeById);
        setPulseIds([beat.nodeId]);
        setFocusMode("ok");
        setFocusBar(`${pathPrefix}${label}`);
        setDemoLabel(`${beat.label} · ${label}`);
        return;
      }

      if (beat.kind === "verse_ref" && beat.ref) {
        const ids = nodeIdsForRef(beat.ref, refToNodeIds);
        setPulseVerseRef(beat.ref);
        if (ids.length) {
          setPulseIds(ids);
          setFocusMode("ok");
          setFocusBar(`${focusPrefix}${beat.ref}`);
        }
        return;
      }

      if (beat.kind === "complete") {
        setPulseIds([]);
        setFocusMode("ok");
        setFocusBar(`${highlightIds.length}${highlightedSuffix}`);
        setDemoRunning(false);
      }
    },
    [focusPrefix, highlightIds.length, highlightedSuffix, nodeById, pathPrefix, refToNodeIds],
  );

  const startEntryDemo = useCallback(() => {
    stopDemo();
    setAutoFocusOn(false);
    setPulseIds([]);

    if (prefersReducedMotion() || pathSpineIds.length < 1) {
      setFocusBar(`${highlightIds.length}${highlightedSuffix}`);
      return;
    }

    const token = demoTokenRef.current + 1;
    demoTokenRef.current = token;
    const beats = buildSubgraphEntryDemoTimeline(pathSpineIds, result.path.verse_refs, demoLabels);

    setDemoRunning(true);
    setDemoProgress(0);
    setDemoLabel(demoLabels.start);

    for (const beat of beats) {
      const timerId = window.setTimeout(() => {
        if (demoTokenRef.current !== token) return;
        runDemoBeat(beat);
      }, beat.at_ms);
      demoTimersRef.current.push(timerId);
    }
  }, [
    demoLabels,
    highlightIds.length,
    highlightedSuffix,
    pathSpineIds,
    result.path.verse_refs,
    runDemoBeat,
    stopDemo,
  ]);

  useEffect(() => {
    if (!autoDemoOnMount || !graphDoc || autoDemoRanRef.current) return;
    if (scriptoriumMode) return;
    if (prefersReducedMotion() || pathSpineIds.length < 1) return;
    autoDemoRanRef.current = true;
    const timer = window.setTimeout(() => {
      setActiveView(productDemoMode ? "storyboard" : "mindmap");
      startEntryDemo();
    }, 520);
    return () => window.clearTimeout(timer);
  }, [autoDemoOnMount, graphDoc, pathSpineIds.length, productDemoMode, scriptoriumMode, startEntryDemo]);

  const mindmapSpineItems = useMemo(() => {
    const ids = reasoningIds.length >= 2 ? reasoningIds : pathSpineIds;
    return ids
      .filter(Boolean)
      .slice(0, 6)
      .map((id) => ({ id, label: nodeLabelFromSlice(id, nodeById) }));
  }, [nodeById, pathSpineIds, reasoningIds]);

  const citationDetail = useMemo(() => {
    if (!citationSelection) return null;
    const shardEntry =
      citationSelection.kind === "verse"
        ? lookupVerseCitationShard(citationSelection.ref, shardDoc)
        : null;
    return buildCitationDetail(citationSelection, result, nodeById, refToNodeIds, shardEntry);
  }, [citationSelection, nodeById, refToNodeIds, result, shardDoc]);

  const selectVerse = useCallback(
    (ref: string, openExplore = false) => {
      stopDemo();
      setAutoFocusOn(false);
      setCitationSelection({ kind: "verse", ref });
      setPulseVerseRef(ref);
      const ids = nodeIdsForRef(ref, refToNodeIds);
      const mapped = ids.length > 0;
      if (mapped) {
        setPulseIds(ids);
        setMeshFocusId(ids[0]);
        setFocusBar(`${focusPrefix}${ref}`);
        setFocusMode("ok");
        if (openExplore) setActiveView("explore");
      } else {
        setPulseIds([]);
        setMeshFocusId(null);
        setFocusBar(`${focusPrefix}${ref} · ${missingInSlice}`);
        setFocusMode("warn");
      }
    },
    [focusPrefix, missingInSlice, refToNodeIds, stopDemo],
  );

  const selectNode = useCallback(
    (nodeId: string) => {
      stopDemo();
      setAutoFocusOn(false);
      setCitationSelection({ kind: "node", nodeId });
      setMeshFocusId(nodeId);
      setPulseIds([nodeId]);
      setFocusBar(`${pathPrefix}${nodeLabelFromSlice(nodeId, nodeById)}`);
      setFocusMode("ok");
      setActiveView("explore");
    },
    [nodeById, pathPrefix, stopDemo],
  );

  const onMindmapVerseClick = useCallback(
    (ref: string) => {
      selectVerse(ref, false);
    },
    [selectVerse],
  );

  const onUserInteract = useCallback(() => {
    stopDemo();
    setAutoFocusOn(false);
    setPulseIds([]);
    setPulseVerseRef(null);
  }, [stopDemo]);

  const applyPulse = useCallback(
    (ids: string[], label: string, mode: "ok" | "warn" = "ok") => {
      onUserInteract();
      setPulseIds(ids);
      setFocusBar(label);
      setFocusMode(mode);
      window.setTimeout(() => setPulseIds([]), 1800);
    },
    [onUserInteract],
  );

  const onVerseRefClick = useCallback(
    (ref: string) => {
      selectVerse(ref, isRefInSlice(ref));
    },
    [isRefInSlice, selectVerse],
  );

  const openExploreWithRef = useCallback(
    (ref: string) => {
      selectVerse(ref, isRefInSlice(ref));
    },
    [isRefInSlice, selectVerse],
  );

  const openCitationExplore = useCallback(() => {
    if (citationSelection?.kind === "verse") {
      selectVerse(citationSelection.ref, isRefInSlice(citationSelection.ref));
    } else if (citationSelection?.kind === "node") {
      selectNode(citationSelection.nodeId);
    }
  }, [citationSelection, isRefInSlice, selectNode, selectVerse]);

  const clearCitation = useCallback(() => {
    setCitationSelection(null);
    setPulseIds([]);
    setPulseVerseRef(null);
    setMeshFocusId(null);
    setFocusBar(null);
  }, []);

  useEffect(() => {
    if (citationPlacement !== "external" || !onCitationSlotChange) return;
    if (!citationDetail) {
      onCitationSlotChange(null);
      return;
    }
    onCitationSlotChange({
      detail: citationDetail,
      onOpenExplore: openCitationExplore,
      onClear: clearCitation,
    });
  }, [
    citationDetail,
    citationPlacement,
    clearCitation,
    onCitationSlotChange,
    openCitationExplore,
  ]);

  useEffect(() => {
    if (citationPlacement !== "external" || !onCitationSlotChange) return;
    return () => onCitationSlotChange(null);
  }, [citationPlacement, onCitationSlotChange]);

  const onPathChipClick = useCallback(
    (nodeId: string) => {
      selectNode(nodeId);
    },
    [selectNode],
  );

  const onNodeClick = useCallback(
    (nodeId: string) => {
      selectNode(nodeId);
    },
    [selectNode],
  );

  useEffect(() => {
    if (!scriptoriumMode) return;
    const onVerse = (event: Event) => {
      const ref = (event as CustomEvent<{ ref?: string }>).detail?.ref;
      if (typeof ref === "string" && ref) onVerseRefClick(ref);
    };
    window.addEventListener("logos-studio-scriptorium-verse-select", onVerse);
    return () => window.removeEventListener("logos-studio-scriptorium-verse-select", onVerse);
  }, [onVerseRefClick, scriptoriumMode]);

  useEffect(() => {
    stopDemo();
    setPulseIds([]);
    setPulseVerseRef(null);
    setAutoFocusOn(false);
    setMeshFocusId(null);
    setActiveView(productDemoMode || scriptoriumMode ? "storyboard" : "mindmap");
    const firstMapped =
      result.path.verse_refs.find((ref) => isRefInSlice(ref)) ?? result.path.verse_refs[0];
    if (firstMapped) {
      setCitationSelection({ kind: "verse", ref: firstMapped });
      const ids = nodeIdsForRef(firstMapped, refToNodeIds);
      if (ids.length) setMeshFocusId(ids[0]);
    } else {
      setCitationSelection(null);
    }
    if (highlightIds.length) {
      setFocusBar(`${highlightIds.length}${highlightedSuffix}`);
      setFocusMode("ok");
    } else {
      setFocusBar(null);
    }
    return () => stopDemo();
  }, [
    highlightIds,
    highlightedSuffix,
    isRefInSlice,
    productDemoMode,
    refToNodeIds,
    result.path.verse_refs,
    result.preset_id,
    scriptoriumMode,
    stopDemo,
  ]);

  const storyboardPayload = useMemo(
    () => ({
      query: result.query ?? "",
      answer: result.answer ?? "",
      query_mode: result.query_mode,
      path: result.path,
      synthesis_meta: result.synthesis_meta,
      conflict_context: result.conflict_context,
      graphrag_meta: result.graphrag_meta,
      evidence_confidence: result.evidence_confidence,
      insight_card: result.insight_card,
    }),
    [result],
  );

  useEffect(() => {
    if (!autoFocusOn || highlightIds.length <= 1) return;
    if (prefersReducedMotion()) return;
    if (activeView !== "explore") return;

    let idx = 0;
    const id = window.setInterval(() => {
      const nodeId = highlightIds[idx % highlightIds.length];
      idx += 1;
      setPulseIds([nodeId]);
      setFocusMode("ok");
      setFocusBar(`${pathPrefix}${nodeLabelFromSlice(nodeId, nodeById)}`);
    }, 2800);
    return () => window.clearInterval(id);
  }, [activeView, autoFocusOn, highlightIds, nodeById, pathPrefix]);

  const renderVerseRefChip = useCallback(
    (ref: string, opts: { keyPrefix?: string; openExploreOnClick?: boolean } = {}) => {
      const mapped = isRefInSlice(ref);
      const active = citationSelection?.kind === "verse" && citationSelection.ref === ref;
      const key = `${opts.keyPrefix ?? ""}${ref}`;
      if (!mapped) {
        return (
          <button
            key={key}
            type="button"
            className={`lr-studio-ref-chip lr-studio-ref-chip--slice-out${
              active ? " lr-studio-ref-chip--active" : ""
            }`}
            onClick={() => selectVerse(ref, false)}
            title={`${missingInSlice} · ${ref}`}
          >
            {ref}
          </button>
        );
      }
      return (
        <button
          key={key}
          type="button"
          className={`lr-studio-ref-chip${active ? " lr-studio-ref-chip--active" : ""}`}
          onClick={() => selectVerse(ref, opts.openExploreOnClick ?? false)}
          title={`${sg?.focus_title ?? "해설 + 망 탐색"} ${ref}`}
        >
          {ref}
        </button>
      );
    },
    [citationSelection, isRefInSlice, missingInSlice, selectVerse, sg?.focus_title],
  );

  const renderExploreView = () => (
    <>
      <div className="lr-studio-graph-head">
        <div className="lr-studio-graph-head-row">
          <div>
            <h3 id="lr-studio-graph-title">
              {productDemoMode ? "입체 관계망 탐색 (Beta)" : "망 탐색 · GPU mesh"}
            </h3>
            {!productDemoMode ? (
              <p className="lr-studio-graph-meta lr-studio-graph-meta--dev">
                Citation Path Mesh explore · 클릭 확장 · wires_to_scoring_core:false · [HYPO]
              </p>
            ) : (
              <p className="lr-studio-graph-meta">
                선택 구절 주변 의미 연결 · 클릭하여 이웃 노드 확장
              </p>
            )}
          </div>
          <div className="lr-studio-graph-hud">
            <span className="lr-studio-graph-hud-pill lr-studio-graph-hud-pill--live">
              {productDemoMode ? "관계망 live" : (sg?.engine_live ?? "경로 엔진 live")}
            </span>
            {nodeCount > 0 ? (
              <span className="lr-studio-graph-hud-pill lr-studio-graph-hud-pill--node-count">
                {meshActive && totalNodeCount > nodeCount
                  ? `${nodeCount}/${totalNodeCount}`
                  : nodeCount}
                {productDemoMode ? "개 노드" : (sg?.node_count_suffix ?? "노드 · citation lock")}
              </span>
            ) : null}
            {meshActive && !productDemoMode ? (
              <span className="lr-studio-graph-hud-pill lr-studio-graph-hud-pill--mesh">
                {sg?.mesh_local ?? "로컬 망"} d{meshDepth}
              </span>
            ) : null}
          </div>
        </div>
        <div className="lr-studio-graph-head-actions">
          {hopIndex ? (
            <label className="lr-studio-mesh-depth" htmlFor="lr-studio-mesh-depth">
              <span>{sg?.mesh_depth ?? "망 깊이"}</span>
              <input
                id="lr-studio-mesh-depth"
                type="range"
                min={1}
                max={MESH_MAX_DEPTH}
                step={1}
                value={meshDepth}
                onChange={(e) => {
                  onUserInteract();
                  setMeshDepth(Number(e.target.value));
                }}
              />
              <span aria-hidden="true">{meshDepth}</span>
            </label>
          ) : null}
          <button type="button" className="lr-studio-autofocus-toggle" onClick={() => setAutoFocusOn((v) => !v)}>
            {autoFocusOn ? (sg?.autofocus_off ?? "자동 포커스 끄기") : (sg?.autofocus_on ?? "자동 포커스 켜기")}
          </button>
          <button type="button" className="lr-studio-autofocus-toggle" onClick={startEntryDemo}>
            {sg?.demo_replay ?? "경로 데모 재생"}
          </button>
        </div>
      </div>

      <div className="lr-studio-graph-legend" aria-label="노드 종류 범례">
        {GRAPH_LEGEND.map((item) => (
          <span key={item.id} className="lr-studio-graph-legend-item">
            <span className="lr-studio-graph-legend-dot" style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
      </div>

      {focusBar ? (
        <p className={`lr-studio-graph-focus lr-studio-graph-focus--${focusMode}`} role="status">
          {focusBar}
        </p>
      ) : null}

      <div className="lr-studio-graph-canvas lr-studio-graph-canvas--stage lr-studio-graph-canvas--explore">
        {demoRunning ? (
          <div className="lr-studio-graph-demo-bar" aria-live="polite">
            <div className="lr-studio-graph-demo-track">
              <div className="lr-studio-graph-demo-fill" style={{ width: `${demoProgress}%` }} />
            </div>
            <span className="lr-studio-graph-demo-label">{demoLabel}</span>
          </div>
        ) : null}

        {loadError ? (
          <p className="lr-studio-graph-error" role="alert">
            {sg?.error_prefix ?? "그래프 슬라이스를 불러올 수 없음:"} {loadError}
          </p>
        ) : graphDoc ? (
          <LogosResearchExploreMeshPanel
            graphDoc={graphDoc}
            hopIndex={hopIndex}
            visibleSeedIds={meshSeedIds}
            meshDepth={meshDepth}
            pathSpineIds={pathSpineIds}
            highlightIds={highlightIds}
            pulseIds={pulseIds}
            height={520}
            externalFocusNodeId={meshFocusId}
            ghostVerseRefs={sliceCoverage.unmappedRefs}
            activeGhostRef={activeGhostRef}
            productDemoMode={productDemoMode}
            onUserInteract={onUserInteract}
            onNodeClick={onNodeClick}
          />
        ) : !loadError ? (
          <p className="lr-studio-graph-loading" aria-busy="true">
            {sg?.loading ?? "경로 망 불러오는 중…"}
          </p>
        ) : null}
      </div>

      {result.path.verse_refs.length ? (
        <div className="lr-studio-graph-refs">
          <span className="lr-studio-graph-refs-label">{sg?.verse_refs ?? "구절 참조"}</span>
          {result.path.verse_refs.map((ref) => renderVerseRefChip(ref, { openExploreOnClick: true }))}
        </div>
      ) : null}

      {reasoningIds.length >= 2 ? (
        <div className="lr-studio-graph-path-chips">
          {reasoningIds.map((nodeId) => (
            <button
              key={nodeId}
              type="button"
              className="lr-studio-path-chip"
              onClick={() => onPathChipClick(nodeId)}
              title={nodeId}
            >
              {nodeLabelFromSlice(nodeId, nodeById)}
            </button>
          ))}
        </div>
      ) : null}
    </>
  );

  return (
    <div
      className={`lr-studio-insight-shell${productDemoMode ? " lr-studio-insight-shell--product-demo" : ""}${scriptoriumMode ? " lr-studio-insight-shell--scriptorium" : ""}`}
      data-product-demo={productDemoMode ? "1" : undefined}
      aria-labelledby="lr-studio-insight-shell-title"
    >
      <div className="lr-studio-view-tabs" role="tablist" aria-label="통찰 뷰 전환">
        <button
          type="button"
          role="tab"
          id="lr-studio-tab-storyboard"
          aria-selected={activeView === "storyboard"}
          aria-controls="lr-studio-panel-storyboard"
          className={`lr-studio-view-tab${activeView === "storyboard" ? " lr-studio-view-tab--active" : ""}`}
          onClick={() => {
            stopDemo();
            setActiveView("storyboard");
          }}
        >
          {scriptoriumMode ? "구조화 분석" : "통찰 스토리보드"}
        </button>
        <button
          type="button"
          role="tab"
          id="lr-studio-tab-mindmap"
          aria-selected={activeView === "mindmap"}
          aria-controls="lr-studio-panel-mindmap"
          className={`lr-studio-view-tab${activeView === "mindmap" ? " lr-studio-view-tab--active" : ""}`}
          onClick={() => {
            stopDemo();
            setActiveView("mindmap");
          }}
        >
          {scriptoriumMode ? "경로 마인드맵" : "경로 마인드맵"}
        </button>
        <button
          type="button"
          role="tab"
          id="lr-studio-tab-explore"
          aria-selected={activeView === "explore"}
          aria-controls="lr-studio-panel-explore"
          className={`lr-studio-view-tab${activeView === "explore" ? " lr-studio-view-tab--active" : ""}`}
          onClick={() => setActiveView("explore")}
          disabled={!graphDoc && !loadError}
        >
          {scriptoriumMode ? "망 탐색" : productDemoMode ? "입체 관계망 (Beta)" : "망 탐색"}
        </button>
      </div>

      <div
        id="lr-studio-panel-mindmap"
        role="tabpanel"
        aria-labelledby="lr-studio-tab-mindmap"
        hidden={activeView !== "mindmap"}
        className="lr-studio-graph-panel lr-studio-graph-panel--mindmap"
      >
        {activeView === "mindmap" ? (
          <LogosResearchPathMindmapPanel
            query={result.query ?? ""}
            presetId={result.preset_id}
            pathSteps={result.path.steps}
            verseRefs={result.path.verse_refs}
            spineItems={mindmapSpineItems}
            meshSummary={{
              graphDoc,
              hopIndex,
              seedIds: meshSeedIds,
              nodeById,
            }}
            pulseGraphNodeIds={pulseIds}
            pulseVerseRef={pulseVerseRef}
            demoProgress={demoProgress}
            demoLabel={demoLabel}
            demoRunning={demoRunning}
            onVerseClick={onMindmapVerseClick}
            onReplayDemo={startEntryDemo}
          />
        ) : null}
      </div>

      <div
        id="lr-studio-panel-storyboard"
        role="tabpanel"
        aria-labelledby="lr-studio-tab-storyboard"
        hidden={activeView !== "storyboard"}
        className="lr-studio-graph-panel lr-studio-graph-panel--storyboard"
      >
        {activeView === "storyboard" ? (
          <LogosResearchStoryboardPanel
            result={storyboardPayload}
            coverage={sliceCoverage}
            onVerseRefClick={openExploreWithRef}
            showAuditorHint={!scriptoriumMode}
            variant={scriptoriumMode ? "scriptorium" : "default"}
            bloomSecondaryHintKo={scriptoriumMode ? bloomSecondaryHint : undefined}
          />
        ) : null}
      </div>

      <div
        id="lr-studio-panel-explore"
        role="tabpanel"
        aria-labelledby="lr-studio-tab-explore"
        hidden={activeView !== "explore"}
        className="lr-studio-graph-panel lr-studio-graph-panel--explore"
      >
        {activeView === "explore" ? renderExploreView() : null}
      </div>

      {!scriptoriumMode && result.path.verse_refs.length ? (
        <div className="lr-studio-graph-refs lr-studio-graph-refs--shared">
          <span className="lr-studio-graph-refs-label">{sg?.verse_refs ?? "구절 참조 · 클릭 시 해설"}</span>
          {result.path.verse_refs.map((ref) =>
            renderVerseRefChip(ref, { keyPrefix: "shared-", openExploreOnClick: true }),
          )}
        </div>
      ) : null}

      {citationPlacement === "inline" && citationDetail ? (
        <LogosResearchCitationSidecarPanel
          detail={citationDetail}
          onOpenExplore={openCitationExplore}
          onClear={clearCitation}
        />
      ) : null}
    </div>
  );
}
