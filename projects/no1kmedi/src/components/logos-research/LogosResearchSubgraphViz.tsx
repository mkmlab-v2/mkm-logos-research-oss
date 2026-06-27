"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ForceGraphMethods } from "react-force-graph-2d";

import type { LogosGraphSliceDoc } from "@/lib/logosResearchGraphTypesV1";
import {
  buildForceGraphData,
  linkColor,
  linkWidth,
  nodeColor,
  nodeRadius,
  type ForceGraphData,
  type ForceGraphLink,
  type ForceGraphNode,
} from "@/lib/logosResearchForceGraphV1";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export type SubgraphVizLabels = {
  zoom_in?: string;
  zoom_out?: string;
  zoom_fit?: string;
  interact_hint?: string;
  layout_simulating?: string;
  layout_ready?: string;
};

type Props = {
  graphDoc: LogosGraphSliceDoc;
  highlightIds: string[];
  pulseIds?: string[];
  pathSpineIds?: string[];
  height?: number;
  labels?: SubgraphVizLabels;
  onNodeClick?: (nodeId: string) => void;
  onUserInteract?: () => void;
};

function shouldDrawNodeLabel(
  id: string,
  highlightSet: Set<string>,
  pulseSet: Set<string>,
  spineSet: Set<string>,
): boolean {
  return highlightSet.has(id) || pulseSet.has(id) || spineSet.has(id);
}

export function LogosResearchSubgraphViz({
  graphDoc,
  highlightIds,
  pulseIds = [],
  pathSpineIds = [],
  height = 480,
  labels,
  onNodeClick,
  onUserInteract,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const didInitialFitRef = useRef(false);

  const [width, setWidth] = useState(640);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [pulsePhase, setPulsePhase] = useState(0);

  const graphData = useMemo<ForceGraphData>(
    () => buildForceGraphData(graphDoc, pathSpineIds, highlightIds),
    [graphDoc, highlightIds, pathSpineIds],
  );

  const highlightSet = useMemo(() => new Set(highlightIds), [highlightIds]);
  const pulseSet = useMemo(() => new Set(pulseIds), [pulseIds]);
  const spineSet = useMemo(() => new Set(pathSpineIds.filter(Boolean)), [pathSpineIds]);
  const hasHighlight = highlightIds.length > 0;
  const isPulsing = pulseIds.length > 0;

  useEffect(() => {
    didInitialFitRef.current = false;
  }, [graphData]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 0) setWidth(Math.floor(w));
    });
    ro.observe(el);
    setWidth(Math.floor(el.clientWidth) || 640);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!isPulsing) return;
    let raf = 0;
    const tick = () => {
      setPulsePhase(performance.now() / 1000);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [isPulsing]);

  const fitNodeIds = useMemo(
    () => new Set([...highlightIds, ...pathSpineIds, ...pulseIds].filter(Boolean)),
    [highlightIds, pathSpineIds, pulseIds],
  );

  const fitHighlight = useCallback(
    (duration = 520) => {
      const fg = fgRef.current;
      if (!fg) return;
      if (fitNodeIds.size > 0) {
        fg.zoomToFit(duration, 80, (n) => {
          if (typeof n.id !== "string") return false;
          return fitNodeIds.has(n.id);
        });
      } else if (hasHighlight) {
        fg.zoomToFit(duration, 56, (n) => {
          if (typeof n.id !== "string") return false;
          return highlightSet.has(n.id) || spineSet.has(n.id);
        });
      } else {
        fg.zoomToFit(duration, 48);
      }
      window.setTimeout(() => setZoomLevel(fg.zoom()), duration + 48);
    },
    [fitNodeIds, hasHighlight, highlightSet, spineSet],
  );

  useEffect(() => {
    if (width < 80) return;
    const timer = window.setTimeout(() => {
      fitHighlight(didInitialFitRef.current ? 400 : 360);
      didInitialFitRef.current = true;
      const fg = fgRef.current;
      if (fg) setZoomLevel(fg.zoom());
    }, didInitialFitRef.current ? 40 : 80);
    return () => window.clearTimeout(timer);
  }, [fitHighlight, fitNodeIds, graphData, width]);

  const zoomBy = useCallback(
    (factor: number) => {
      const fg = fgRef.current;
      if (!fg) return;
      onUserInteract?.();
      const next = Math.min(8, Math.max(0.12, fg.zoom() * factor));
      fg.zoom(next, 240);
      setZoomLevel(next);
    },
    [onUserInteract],
  );

  const resetView = useCallback(() => {
    onUserInteract?.();
    fitHighlight(420);
  }, [fitHighlight, onUserInteract]);

  const resolveLinkEndpoint = useCallback((endpoint: string | ForceGraphNode) => {
    return typeof endpoint === "string" ? endpoint : endpoint.id;
  }, []);

  const nodeIdOf = useCallback((node: { id?: string | number }) => {
    return typeof node.id === "string" ? node.id : "";
  }, []);

  const asForceNode = useCallback((node: { id?: string | number }) => node as ForceGraphNode, []);

  return (
    <div ref={containerRef} className="lr-studio-graph-interactive" style={{ height }}>
      <div className="lr-studio-graph-zoom" role="toolbar" aria-label="그래프 확대/축소">
        <button type="button" className="lr-studio-graph-zoom-btn" onClick={() => zoomBy(1.18)} title={labels?.zoom_in ?? "확대"}>
          +
        </button>
        <button type="button" className="lr-studio-graph-zoom-btn" onClick={() => zoomBy(0.85)} title={labels?.zoom_out ?? "축소"}>
          −
        </button>
        <button
          type="button"
          className="lr-studio-graph-zoom-btn lr-studio-graph-zoom-btn--text"
          onClick={() => fitHighlight(420)}
          title={labels?.zoom_fit ?? "맞춤"}
        >
          {labels?.zoom_fit ?? "맞춤"}
        </button>
        <button type="button" className="lr-studio-graph-zoom-btn lr-studio-graph-zoom-btn--text" onClick={resetView} title="초기화">
          초기화
        </button>
        <span className="lr-studio-graph-zoom-level">{Math.round(zoomLevel * 100)}%</span>
      </div>

      <p className="lr-studio-graph-interact-hint">
        {labels?.interact_hint ?? "드래그 이동 · 스크롤 확대/축소 · 노드 드래그"}
      </p>

      <p className="lr-studio-graph-layout-badge lr-studio-graph-layout-badge--ready" aria-live="polite">
        {labels?.layout_ready ?? "고정 배치 · 직접 조작 가능"}
      </p>

      <ForceGraph2D
        ref={fgRef}
        width={width}
        height={height}
        graphData={graphData}
        backgroundColor="rgba(0,0,0,0)"
        nodeId="id"
        nodeLabel="name"
        linkSource="source"
        linkTarget="target"
        cooldownTicks={0}
        warmupTicks={0}
        d3AlphaMin={0}
        d3AlphaDecay={1}
        autoPauseRedraw={!isPulsing}
        enableNodeDrag
        enableZoomInteraction
        enablePanInteraction
        minZoom={0.12}
        maxZoom={8}
        onNodeClick={(node) => {
          onUserInteract?.();
          if (typeof node.id === "string") onNodeClick?.(node.id);
        }}
        onNodeDrag={(node) => {
          onUserInteract?.();
          node.fx = node.x;
          node.fy = node.y;
        }}
        onNodeDragEnd={(node) => {
          node.fx = node.x;
          node.fy = node.y;
        }}
        onZoom={(transform) => setZoomLevel(transform.k)}
        onBackgroundClick={() => onUserInteract?.()}
        nodeVal={(node) => {
          const id = nodeIdOf(node);
          return nodeRadius(
            asForceNode(node),
            highlightSet.has(id),
            pulseSet.has(id),
            pulsePhase,
            hasHighlight,
          );
        }}
        nodeColor={(node) => {
          const id = nodeIdOf(node);
          return nodeColor(
            asForceNode(node),
            highlightSet.has(id),
            pulseSet.has(id),
            hasHighlight,
            spineSet.has(id),
          );
        }}
        nodeCanvasObjectMode={(node) => {
          const id = nodeIdOf(node);
          return shouldDrawNodeLabel(id, highlightSet, pulseSet, spineSet) ? "after" : undefined;
        }}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const id = nodeIdOf(node);
          const forceNode = asForceNode(node);
          if (!shouldDrawNodeLabel(id, highlightSet, pulseSet, spineSet)) return;

          const isHighlight = highlightSet.has(id);
          const isPulse = pulseSet.has(id);
          const isSpineOnly = spineSet.has(id) && !isHighlight && !isPulse;

          const r = nodeRadius(forceNode, isHighlight, isPulse, pulsePhase, hasHighlight);

          if (isPulse) {
            const glowR = r + Math.max(6 / globalScale, 2);
            ctx.beginPath();
            ctx.arc(node.x || 0, node.y || 0, glowR, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(255,255,255,0.12)";
            ctx.fill();
          }

          const label = forceNode.name || id.split("::").pop() || id;
          const fontSize = Math.max((isSpineOnly ? 10 : 11) / globalScale, 3);
          ctx.font = `${isSpineOnly ? 500 : 600} ${fontSize}px sans-serif`;
          ctx.fillStyle = isPulse ? "#ffffff" : isSpineOnly ? "#fcd34d" : "#f1f5f9";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(label, node.x || 0, (node.y || 0) + fontSize * 1.15);
        }}
        linkColor={(link) =>
          linkColor(
            link as ForceGraphLink,
            resolveLinkEndpoint(link.source as string | ForceGraphNode),
            resolveLinkEndpoint(link.target as string | ForceGraphNode),
            highlightSet,
            pulseSet,
            hasHighlight,
          )
        }
        linkWidth={(link) =>
          linkWidth(
            link as ForceGraphLink,
            resolveLinkEndpoint(link.source as string | ForceGraphNode),
            resolveLinkEndpoint(link.target as string | ForceGraphNode),
            highlightSet,
            pulseSet,
            hasHighlight,
          )
        }
      />
    </div>
  );
}
