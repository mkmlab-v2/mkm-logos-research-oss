"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ForceGraphMethods } from "react-force-graph-2d";

import type { GraphBundleV1 } from "@/lib/clinicianGraphTypesV1";
import {
  buildClinicianForceGraphData,
  clinicianLinkColor,
  clinicianLinkWidth,
  clinicianNodeColor,
  clinicianNodeRadius,
  type ClinicianForceGraphLink,
  type ClinicianForceGraphNode,
} from "@/lib/clinicianGraphForceGraphV1";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

type Props = {
  graphBundle: GraphBundleV1;
  height?: number;
  onNodeClick?: (nodeId: string) => void;
};

export function ClinicianConsultGraphViz({ graphBundle, height = 320, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);
  const [width, setWidth] = useState(640);
  const [selectedId, setSelectedId] = useState<string | undefined>();

  const graphData = useMemo(() => buildClinicianForceGraphData(graphBundle), [graphBundle]);

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
    const t = window.setTimeout(() => fgRef.current?.zoomToFit(400, 48), 120);
    return () => window.clearTimeout(t);
  }, [graphData]);

  const handleNodeClick = useCallback(
    (node: { id?: string | number }) => {
      if (typeof node.id !== "string") return;
      setSelectedId(node.id);
      onNodeClick?.(node.id);
    },
    [onNodeClick],
  );

  if (!graphData.nodes.length) {
    return <p className="workspace-muted">시각화할 노드가 없습니다.</p>;
  }

  return (
    <div ref={containerRef} className="consult-graph-viz-wrap">
      <ForceGraph2D
        ref={fgRef}
        width={width}
        height={height}
        graphData={graphData}
        nodeRelSize={1}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={0.92}
        cooldownTicks={0}
        enableNodeDrag={false}
        onNodeClick={handleNodeClick}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const n = node as ClinicianForceGraphNode;
          const r = clinicianNodeRadius(n, selectedId) / globalScale;
          ctx.beginPath();
          ctx.arc(n.x || 0, n.y || 0, r, 0, 2 * Math.PI, false);
          ctx.fillStyle = clinicianNodeColor(n);
          ctx.fill();
          if (n.id === selectedId) {
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 2 / globalScale;
            ctx.stroke();
          }
          if (globalScale > 0.55) {
            ctx.font = `${10 / globalScale}px sans-serif`;
            ctx.fillStyle = "#e2e8f0";
            ctx.fillText(n.name, (n.x || 0) + r + 2, (n.y || 0) + 3);
          }
        }}
        linkColor={() => "rgba(61, 155, 132, 0.35)"}
        linkWidth={(link) => clinicianLinkWidth(link as ClinicianForceGraphLink)}
      />
      <p className="workspace-muted consult-graph-viz-legend">
        검토 보조 시각화 · NON_GATING=주황 · 자동 확정 아님
      </p>
    </div>
  );
}
