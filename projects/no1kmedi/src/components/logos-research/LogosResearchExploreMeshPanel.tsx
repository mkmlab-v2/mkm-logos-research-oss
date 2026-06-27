"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  buildExploreMeshSnapshot,
  expandVisibleFromClick,
  EXPLORE_FIT_VIEW_MIN_NODES,
  EXPLORE_MESH_CLICK_EXPAND_HOPS,
  EXPLORE_MESH_EXPAND_MAX,
  ghostNodeIdForRef,
  hopDistanceMap,
  isGhostNodeId,
  nodeLabel,
  snapshotPositionsToCache,
  type ExploreMeshSnapshot,
  type ExplorePositionCache,
} from "@/lib/logosResearchExploreMeshV1";
import type { LensContextMeshHopIndexDoc } from "@/lib/lensContextMeshBfsV1";
import { bfsVisibleNodeIds } from "@/lib/lensContextMeshBfsV1";
import type { LogosGraphSliceDoc } from "@/lib/logosResearchGraphTypesV1";
import type { LogosGraphSliceNode } from "@/lib/logosResearchHighlightV1";

const MESH_BOOT_TIMEOUT_MS = 30_000;

function promiseWithTimeout<T>(promise: Promise<T>, timeoutMs: number, label: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(`${label}_timeout_${Math.round(timeoutMs / 1000)}s`));
    }, timeoutMs);
    promise.then(
      (value) => {
        window.clearTimeout(timer);
        resolve(value);
      },
      (err) => {
        window.clearTimeout(timer);
        reject(err);
      },
    );
  });
}
type GraphInstance = {
  setPointPositions: (p: Float32Array, dontRescale?: boolean) => void;
  setPointColors: (c: Float32Array) => void;
  setPointSizes: (s: Float32Array) => void;
  setLinks: (l: Float32Array) => void;
  setLinkWidths: (w: Float32Array) => void;
  render: (simulationAlpha?: number) => void;
  unpause: () => void;
  fitView: (duration?: number, padding?: number, enableSimulation?: boolean) => void;
  fitViewByPointIndices: (
    indices: number[],
    duration?: number,
    padding?: number,
    enableSimulation?: boolean,
  ) => void;
  zoomToPointByIndex: (
    index: number,
    duration?: number,
    scale?: number,
    canZoomOut?: boolean,
    enableSimulation?: boolean,
  ) => void;
  spaceToScreenPosition?: (spacePosition: [number, number]) => [number, number];
  trackPointPositionsByIndices?: (indices: number[]) => void;
  getTrackedPointPositionsMap?: () => ReadonlyMap<number, [number, number]>;
  destroy: () => void;
  ready: Promise<void>;
  isReady: boolean;
};

type LabelSlot = {
  x: number;
  y: number;
  text: string;
  kind: "focus" | "spine" | "ghost";
};

type Props = {
  graphDoc: LogosGraphSliceDoc;
  hopIndex: LensContextMeshHopIndexDoc | null;
  visibleSeedIds: string[];
  meshDepth: number;
  pathSpineIds: string[];
  highlightIds: string[];
  pulseIds?: string[];
  height?: number;
  externalFocusNodeId?: string | null;
  ghostVerseRefs?: string[];
  activeGhostRef?: string | null;
  productDemoMode?: boolean;
  onNodeClick?: (nodeId: string) => void;
  onUserInteract?: () => void;
};

export function LogosResearchExploreMeshPanel({
  graphDoc,
  hopIndex,
  visibleSeedIds,
  meshDepth,
  pathSpineIds,
  highlightIds,
  pulseIds = [],
  height = 520,
  externalFocusNodeId = null,
  ghostVerseRefs = [],
  activeGhostRef = null,
  productDemoMode = false,
  onNodeClick,
  onUserInteract,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<GraphInstance | null>(null);
  const idsRef = useRef<string[]>([]);
  const labelTargetsRef = useRef<Map<number, { text: string; kind: LabelSlot["kind"] }>>(new Map());
  const labelSlotsRef = useRef<LabelSlot[]>([]);
  const snapshotRef = useRef<ExploreMeshSnapshot | null>(null);
  const positionCacheRef = useRef<ExplorePositionCache>(new Map());
  const [focusId, setFocusId] = useState<string | null>(null);
  const [expandCount, setExpandCount] = useState(0);
  const [simState, setSimState] = useState<"boot" | "live" | "error">("boot");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [labelSlots, setLabelSlots] = useState<LabelSlot[]>([]);

  const initialVisible = useMemo(() => {
    if (hopIndex && visibleSeedIds.length) {
      return bfsVisibleNodeIds(hopIndex, visibleSeedIds, meshDepth, EXPLORE_MESH_EXPAND_MAX);
    }
    const fallback = new Set<string>();
    for (const id of [...pathSpineIds, ...highlightIds]) if (id) fallback.add(id);
    return fallback;
  }, [highlightIds, hopIndex, meshDepth, pathSpineIds, visibleSeedIds]);

  const [visibleIds, setVisibleIds] = useState<Set<string>>(initialVisible);

  useEffect(() => {
    if (!externalFocusNodeId) return;
    setFocusId(externalFocusNodeId);
    if (hopIndex) {
      setVisibleIds((prev) =>
        expandVisibleFromClick(hopIndex, prev, externalFocusNodeId, EXPLORE_MESH_EXPAND_MAX),
      );
    }
  }, [externalFocusNodeId, hopIndex]);

  useEffect(() => {
    if (!activeGhostRef) return;
    setFocusId(ghostNodeIdForRef(activeGhostRef));
  }, [activeGhostRef]);

  useEffect(() => {
    setVisibleIds(initialVisible);
    if (!externalFocusNodeId && !activeGhostRef) setFocusId(null);
    setExpandCount(0);
    positionCacheRef.current = new Map();
  }, [graphDoc, initialVisible, externalFocusNodeId, activeGhostRef]);

  const nodeById = useMemo(() => {
    const map: Record<string, LogosGraphSliceNode> = {};
    for (const n of graphDoc.nodes || []) map[n.id] = n;
    for (const ref of ghostVerseRefs) {
      const gid = ghostNodeIdForRef(ref);
      map[gid] = { id: gid, kind: "ghost", label: ref, ref };
    }
    return map;
  }, [ghostVerseRefs, graphDoc.nodes]);

  const hopDistances = useMemo(() => {
    if (!hopIndex || !focusId || isGhostNodeId(focusId)) return new Map<string, number>();
    return hopDistanceMap(hopIndex, focusId, 8);
  }, [focusId, hopIndex]);

  const ghostAnchorId = useMemo(() => {
    if (externalFocusNodeId && visibleIds.has(externalFocusNodeId)) return externalFocusNodeId;
    for (const id of pathSpineIds) if (visibleIds.has(id)) return id;
    for (const id of highlightIds) if (visibleIds.has(id)) return id;
    return visibleSeedIds.find((id) => visibleIds.has(id)) ?? null;
  }, [externalFocusNodeId, highlightIds, pathSpineIds, visibleIds, visibleSeedIds]);

  const snapshot = useMemo(
    () =>
      buildExploreMeshSnapshot(graphDoc, visibleIds, {
        pathSpineIds,
        highlightIds: [...highlightIds, ...pulseIds],
        focusId: focusId && !isGhostNodeId(focusId) ? focusId : null,
        hopDistances,
        ghostRefs: ghostVerseRefs,
        activeGhostRef,
        positionCache: positionCacheRef.current,
        ghostAnchorId,
      }),
    [
      graphDoc,
      visibleIds,
      pathSpineIds,
      highlightIds,
      pulseIds,
      focusId,
      hopDistances,
      ghostVerseRefs,
      activeGhostRef,
      ghostAnchorId,
    ],
  );

  const resolveLabelNodeIds = useCallback((): string[] => {
    if (!snapshot) return [];
    const ids: string[] = [];
    if (activeGhostRef) ids.push(ghostNodeIdForRef(activeGhostRef));
    if (focusId && snapshot.idToIndex.has(focusId)) ids.push(focusId);
    for (const id of pathSpineIds) {
      if (snapshot.idToIndex.has(id) && !ids.includes(id)) ids.push(id);
      if (ids.length >= 6) break;
    }
    return [...new Set(ids)].slice(0, 6);
  }, [activeGhostRef, focusId, pathSpineIds, snapshot]);

  const labelSlotsChanged = (next: LabelSlot[], prev: LabelSlot[]) => {
    if (next.length !== prev.length) return true;
    for (let i = 0; i < next.length; i += 1) {
      const a = next[i];
      const b = prev[i];
      if (a.text !== b.text || a.kind !== b.kind) return true;
      if (Math.abs(a.x - b.x) > 0.45 || Math.abs(a.y - b.y) > 0.45) return true;
    }
    return false;
  };

  const syncLabelTargets = useCallback(() => {
    const graph = graphRef.current;
    snapshotRef.current = snapshot ?? null;
    if (!graph?.isReady || !snapshot || !graph.spaceToScreenPosition) {
      labelTargetsRef.current = new Map();
      graph?.trackPointPositionsByIndices?.([]);
      labelSlotsRef.current = [];
      setLabelSlots([]);
      return;
    }
    const targetMap = new Map<number, { text: string; kind: LabelSlot["kind"] }>();
    for (const id of resolveLabelNodeIds()) {
      const idx = snapshot.idToIndex.get(id);
      if (idx == null) continue;
      const kind: LabelSlot["kind"] = isGhostNodeId(id)
        ? "ghost"
        : focusId === id || (activeGhostRef && ghostNodeIdForRef(activeGhostRef) === id)
          ? "focus"
          : "spine";
      targetMap.set(idx, { text: nodeLabel(nodeById[id] || { id }), kind });
    }
    labelTargetsRef.current = targetMap;
    graph.trackPointPositionsByIndices?.([...targetMap.keys()]);
  }, [activeGhostRef, focusId, nodeById, resolveLabelNodeIds, snapshot]);

  const paintLabelSlots = useCallback(() => {
    const graph = graphRef.current;
    const snap = snapshotRef.current;
    const targets = labelTargetsRef.current;
    if (!graph?.isReady || !graph.spaceToScreenPosition || !snap || targets.size === 0) {
      if (labelSlotsRef.current.length) {
        labelSlotsRef.current = [];
        setLabelSlots([]);
      }
      return;
    }
    const tracked = graph.getTrackedPointPositionsMap?.();
    const slots: LabelSlot[] = [];
    for (const [idx, meta] of targets) {
      const trackedPos = tracked?.get(idx);
      const sx = trackedPos?.[0] ?? snap.positions[idx * 2];
      const sy = trackedPos?.[1] ?? snap.positions[idx * 2 + 1];
      const [x, y] = graph.spaceToScreenPosition([sx, sy]);
      slots.push({ x, y, text: meta.text, kind: meta.kind });
    }
    if (labelSlotsChanged(slots, labelSlotsRef.current)) {
      labelSlotsRef.current = slots;
      setLabelSlots(slots);
    }
  }, []);

  const applySnapshot = useCallback(
    (graph: GraphInstance, fit = false) => {
      if (!snapshot) return;
      idsRef.current = snapshot.ids;
      positionCacheRef.current = snapshotPositionsToCache(snapshot);
      const preserveLayout = !fit && expandCount > 0;
      graph.setPointPositions(snapshot.positions, preserveLayout);
      graph.setPointColors(snapshot.colors);
      graph.setPointSizes(snapshot.sizes);
      graph.setLinks(snapshot.links);
      graph.setLinkWidths(snapshot.linkWidths);
      graph.render(preserveLayout ? 0.45 : 0.92);
      graph.unpause();

      const pivotId =
        (activeGhostRef ? ghostNodeIdForRef(activeGhostRef) : null) ||
        (focusId && snapshot.idToIndex.has(focusId) ? focusId : null) ||
        ghostAnchorId;
      const pivotIdx = pivotId != null ? snapshot.idToIndex.get(pivotId) : undefined;

      if (fit) {
        const nodeTotal = snapshot.ids.length;
        const spineIndices = pathSpineIds
          .map((id) => snapshot.idToIndex.get(id))
          .filter((i): i is number => i != null);
        const allIndices = snapshot.ids
          .map((id) => snapshot.idToIndex.get(id))
          .filter((i): i is number => i != null);

        if (nodeTotal < EXPLORE_FIT_VIEW_MIN_NODES) {
          const pivot =
            pivotIdx ??
            (spineIndices.length ? spineIndices[Math.floor(spineIndices.length / 2)] : undefined) ??
            allIndices[0];
          if (pivot != null) {
            graph.zoomToPointByIndex(pivot, 520, 1.55, false, true);
          } else if (spineIndices.length >= 2) {
            graph.fitViewByPointIndices(spineIndices, 520, 0.12, true);
          }
        } else if (spineIndices.length >= 2) {
          graph.fitViewByPointIndices(spineIndices, 680, 0.32, true);
        } else {
          graph.fitView(680, 0.32, true);
        }
      } else if (pivotIdx != null) {
        graph.zoomToPointByIndex(pivotIdx, 420, 1.65, true, true);
      }
      syncLabelTargets();
      window.setTimeout(() => paintLabelSlots(), fit ? 560 : 320);
    },
    [activeGhostRef, expandCount, focusId, ghostAnchorId, paintLabelSlots, pathSpineIds, snapshot, syncLabelTargets],
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let cancelled = false;
    let graph: GraphInstance | null = null;

    (async () => {
      try {
        const mod = await import("@cosmos.gl/graph");
        if (cancelled || !containerRef.current) return;
        graph = new mod.Graph(containerRef.current, {
          backgroundColor: "transparent",
          spaceSize: 2048,
          simulationRepulsion: 1.15,
          simulationRepulsionTheta: 0.8,
          simulationLinkSpring: 0.14,
          simulationLinkDistance: 42,
          simulationFriction: 0.42,
          simulationGravity: 0.06,
          enableSimulation: true,
          enableDrag: true,
          fitViewOnInit: false,
          rescalePositions: true,
          pointSizeScale: 1.05,
          curvedLinks: true,
          linkDefaultWidth: 0.6,
          linkDefaultColor: [0.55, 0.62, 0.72, 0.28],
          onPointClick: (index) => {
            onUserInteract?.();
            const id = idsRef.current[index];
            if (!id) return;
            if (isGhostNodeId(id)) return;
            setFocusId(id);
            if (hopIndex) {
              setVisibleIds((prev) =>
                expandVisibleFromClick(hopIndex, prev, id, EXPLORE_MESH_EXPAND_MAX),
              );
              setExpandCount((c) => c + EXPLORE_MESH_CLICK_EXPAND_HOPS);
            }
            onNodeClick?.(id);
            const g = graphRef.current;
            if (g?.isReady) {
              g.zoomToPointByIndex(index, 520, 1.8, true, true);
            }
          },
        }) as GraphInstance;
        graphRef.current = graph;
        await promiseWithTimeout(graph.ready, MESH_BOOT_TIMEOUT_MS, "cosmos_graph_ready");
        if (cancelled) {
          graph.destroy();
          return;
        }
        setSimState("live");
        setLoadError(null);
      } catch (e: unknown) {
        if (!cancelled) {
          setSimState("error");
          graph?.destroy();
          graphRef.current = null;
          setLoadError(e instanceof Error ? e.message : "cosmos_init_failed");
        }
      }
    })();

    return () => {
      cancelled = true;
      graphRef.current?.destroy();
      graphRef.current = null;
    };
  }, [hopIndex, onNodeClick, onUserInteract]);

  useEffect(() => {
    const graph = graphRef.current;
    if (!graph?.isReady || !snapshot || simState !== "live") return;
    const shouldFit = expandCount === 0;
    applySnapshot(graph, shouldFit);
  }, [applySnapshot, expandCount, simState, snapshot]);

  useEffect(() => {
    if (simState !== "live") return;
    let running = true;
    const tick = () => {
      if (!running) return;
      paintLabelSlots();
      requestAnimationFrame(tick);
    };
    const rafId = requestAnimationFrame(tick);
    return () => {
      running = false;
      cancelAnimationFrame(rafId);
    };
  }, [paintLabelSlots, simState]);

  useEffect(() => {
    if (simState !== "live") return;
    syncLabelTargets();
    paintLabelSlots();
  }, [paintLabelSlots, simState, syncLabelTargets]);

  const focusLabel = focusId ? nodeLabel(nodeById[focusId] || { id: focusId }) : null;

  return (
    <div
      className="lr-studio-explore-mesh"
      data-logos-explore-mesh="1"
      data-logos-explore-node-count={visibleIds.size}
      data-logos-explore-ghost-count={snapshot?.ghostCount ?? 0}
      data-logos-explore-label-count={labelSlots.length}
      data-logos-explore-label-sync="raf"
      data-logos-explore-expand-count={expandCount}
      data-logos-explore-sim={simState}
      style={{ height }}
    >
      <div className="lr-studio-explore-mesh-hud" role="status">
        <span className="lr-studio-graph-hud-pill lr-studio-graph-hud-pill--live">
          {productDemoMode ? "실시간 의미 관계도" : "GPU mesh · cosmos.gl"}
        </span>
        <span className="lr-studio-graph-hud-pill">
          {productDemoMode
            ? `${visibleIds.size}개 연결 · 클릭하여 확장`
            : `${visibleIds.size} 노드 · 클릭 확장 ${expandCount}`}
        </span>
        {(snapshot?.ghostCount ?? 0) > 0 ? (
          <span
            className="lr-studio-graph-hud-pill lr-studio-graph-hud-pill--ghost"
            title="슬라이스 외 구절 · [HYPO] 탐색 중 표시"
          >
            {productDemoMode
              ? `탐색 중 ${snapshot?.ghostCount}`
              : `ghost ${snapshot?.ghostCount} · [HYPO]`}
          </span>
        ) : null}
        {focusLabel ? (
          <span className="lr-studio-graph-hud-pill lr-studio-graph-hud-pill--mesh">
            포커스 · {focusLabel}
          </span>
        ) : productDemoMode ? null : (
          <span className="lr-studio-graph-hud-pill lr-studio-graph-hud-pill--mesh">
            노드 클릭 → 이웃 망 확장 · [HYPO]
          </span>
        )}
      </div>

      {loadError ? (
        <p className="lr-studio-graph-error" role="alert">
          Explore mesh 초기화 실패: {loadError}
        </p>
      ) : null}

      <div
        ref={containerRef}
        className="lr-studio-explore-mesh-canvas"
        style={{ height: height - 44 }}
        aria-label="Logos explore mesh GPU canvas"
      >
        {labelSlots.length ? (
          <div className="lr-studio-explore-mesh-labels" aria-hidden="true">
            {labelSlots.map((slot) => (
              <span
                key={`${slot.kind}-${slot.text}`}
                className={`lr-studio-explore-mesh-label lr-studio-explore-mesh-label--${slot.kind}`}
                style={{ left: slot.x, top: slot.y }}
              >
                {slot.text}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {simState === "boot" && !loadError ? (
        <p className="lr-studio-graph-loading lr-studio-explore-mesh-boot" aria-busy="true">
          GPU 물리 엔진 기동 중… (최대 {Math.round(MESH_BOOT_TIMEOUT_MS / 1000)}초)
        </p>
      ) : null}
    </div>
  );
}
