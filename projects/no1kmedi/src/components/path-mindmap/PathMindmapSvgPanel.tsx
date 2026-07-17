"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  ASK_GRAPH_EDGE_LABEL_KO,
  ASK_GRAPH_EDGE_LABEL_SHORT,
  edgeRelationCssClass,
  presentEdgeRelationTypes,
  resolveAskGraphEdgeRelation,
  type AskGraphEdgeRelation,
} from "@/lib/logosAskGraphEdgeTypesV1";
import {
  curvedEdgePath,
  layoutPathMindmapRadial,
  type MindmapLayoutNode,
  type PathMindmapModel,
} from "@/lib/pathMindmapCoreV1";
import { prefersReducedMotion } from "@/lib/logosResearchSubgraphDemoV1";

export type PathMindmapKindStyle = {
  fill: string;
  stroke: string;
  text: string;
  r: number;
};

export type PathMindmapSvgPanelProps = {
  model: PathMindmapModel;
  layoutFn?: (model: PathMindmapModel, width: number, height: number) => MindmapLayoutNode[];
  layout?: MindmapLayoutNode[];
  kindStyles: Record<string, PathMindmapKindStyle>;
  activeIds?: Set<string>;
  title: string;
  meta: string;
  footnote: string;
  svgTitle: string;
  height?: number;
  className?: string;
  panelDataAttributes?: Record<string, string>;
  gradientId?: string;
  gradientInner?: string;
  gradientOuter?: string;
  leafKinds?: string[];
  onLeafClick?: (node: MindmapLayoutNode) => void;
  nodeTooltips?: Record<string, string>;
  disablePulseAnimation?: boolean;
  demoProgress?: number;
  demoLabel?: string;
  demoRunning?: boolean;
  onReplayDemo?: () => void;
  replayLabel?: string;
  /** When set, query/title renders above the SVG; root circle stays icon-only. */
  externalRootCaption?: string;
  /** D-VIZ-2: show edge-type color legend (default true when typed edges present). */
  showEdgeLegend?: boolean;
  /** D-VIZ-2: mid-edge short labels when edge count ≤ labelEdgeBudget. */
  showEdgeTypeLabels?: boolean;
  labelEdgeBudget?: number;
  /** Ask compact: calm path ordinals (1·2) instead of repeating 「경로」; never 「인용」. */
  pathOrdinalLabels?: boolean;
};

export function PathMindmapSvgPanel({
  model,
  layoutFn,
  layout: layoutProp,
  kindStyles,
  activeIds = new Set(),
  title,
  meta,
  footnote,
  svgTitle,
  height = 480,
  className = "lr-studio-mindmap-wrap",
  panelDataAttributes,
  gradientId = "path-mm-bg-glow",
  gradientInner = "#e8f5f1",
  gradientOuter = "#faf7f2",
  leafKinds = ["verse"],
  onLeafClick,
  nodeTooltips,
  disablePulseAnimation = false,
  demoProgress = 0,
  demoLabel,
  demoRunning = false,
  onReplayDemo,
  replayLabel = "경로 데모 재생",
  externalRootCaption,
  showEdgeLegend = true,
  showEdgeTypeLabels = true,
  labelEdgeBudget = 16,
  pathOrdinalLabels = false,
}: PathMindmapSvgPanelProps) {
  function summarizeNodeLabel(node: MindmapLayoutNode): string {
    const raw = (node.label || "").replace(/\s+/g, " ").trim();
    if (!raw) return "";
    if (node.kind === "verse") {
      const cap = 22;
      return raw.length > cap ? `${raw.slice(0, cap - 1)}…` : raw;
    }
    if (node.kind === "root") return "";
    const cap = node.kind === "spine" ? 18 : 20;
    return raw.length > cap ? `${raw.slice(0, cap - 1)}…` : raw;
  }

  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(720);
  const [pulsePhase, setPulsePhase] = useState(0);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const hoveredTooltip =
    hoveredNodeId && nodeTooltips?.[hoveredNodeId] ? nodeTooltips[hoveredNodeId] : null;

  const layout = useMemo(() => {
    if (layoutProp) return layoutProp;
    const fn =
      layoutFn ??
      ((m: PathMindmapModel, w: number, h: number) => layoutPathMindmapRadial(m, w, h));
    return fn(model, width, height);
  }, [height, layoutFn, layoutProp, model, width]);

  const layoutById = useMemo(() => new Map(layout.map((n) => [n.id, n])), [layout]);
  const leafSet = useMemo(() => new Set(leafKinds), [leafKinds]);
  const nodeById = useMemo(() => new Map(model.nodes.map((n) => [n.id, n])), [model.nodes]);
  const presentRelations = useMemo(() => presentEdgeRelationTypes(model), [model]);
  const paintLabels =
    showEdgeTypeLabels && model.edges.length > 0 && model.edges.length <= labelEdgeBudget;
  /** Path-order index for sequential edges — visual bridge weight (≠ lemma betweenness claim). */
  const pathEdgeOrder = useMemo(() => {
    const order = new Map<string, number>();
    let i = 0;
    for (const edge of model.edges) {
      const relation = resolveAskGraphEdgeRelation(edge, nodeById);
      if (relation !== "path_sequential") continue;
      order.set(`${edge.from}|${edge.to}`, i);
      i += 1;
    }
    return { order, count: i };
  }, [model.edges, nodeById]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 0) setWidth(Math.floor(w));
    });
    ro.observe(el);
    setWidth(Math.floor(el.clientWidth) || 720);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!activeIds.size || prefersReducedMotion() || disablePulseAnimation) return;
    let raf = 0;
    const tick = () => {
      setPulsePhase(performance.now() / 1000);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [activeIds.size, disablePulseAnimation]);

  const typedAttrs: Record<string, string> = {
    "data-logos-edge-typed": "1",
    ...(presentRelations.length
      ? { "data-logos-edge-types": presentRelations.join(",") }
      : {}),
  };

  return (
    <div
      className={className}
      ref={containerRef}
      {...panelDataAttributes}
      {...typedAttrs}
      aria-label={title}
    >
      <div className="lr-studio-mindmap-head">
        <div>
          <h3 className="lr-studio-mindmap-title">{title}</h3>
          <p className="lr-studio-mindmap-meta">{meta}</p>
        </div>
        {onReplayDemo ? (
          <button type="button" className="lr-studio-mindmap-replay" onClick={onReplayDemo}>
            {replayLabel}
          </button>
        ) : null}
      </div>

      {showEdgeLegend && presentRelations.length > 0 ? (
        <ul className="lr-studio-mindmap-edge-legend" aria-label="연결 유형">
          {presentRelations.map((rel: AskGraphEdgeRelation) => (
            <li
              key={rel}
              className={`lr-studio-mindmap-edge-legend-item lr-studio-mindmap-edge-legend-item--${rel}`}
            >
              <span
                className={`lr-studio-mindmap-edge-swatch lr-studio-mindmap-edge-swatch--${rel}`}
                aria-hidden
              />
              <span>{ASK_GRAPH_EDGE_LABEL_KO[rel]}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {demoRunning && demoLabel ? (
        <div className="lr-studio-mindmap-demo-bar" aria-live="polite">
          <div className="lr-studio-mindmap-demo-track">
            <span className="lr-studio-mindmap-demo-fill" style={{ width: `${demoProgress}%` }} />
          </div>
          <span className="lr-studio-mindmap-demo-label">{demoLabel}</span>
        </div>
      ) : null}

      {externalRootCaption ? (
        <p className="lr-studio-mindmap-root-caption" title={externalRootCaption}>
          {externalRootCaption}
        </p>
      ) : null}

      <div className="lr-studio-mindmap-stage" style={{ minHeight: height }}>
        <svg
          className="lr-studio-mindmap-svg"
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height={height}
          role="img"
          aria-labelledby="path-mindmap-svg-title"
        >
          <title id="path-mindmap-svg-title">{svgTitle}</title>
          <defs>
            <radialGradient id={gradientId} cx="50%" cy="50%" r="55%">
              <stop offset="0%" stopColor={gradientInner} stopOpacity="0.95" />
              <stop offset="100%" stopColor={gradientOuter} stopOpacity="0.2" />
            </radialGradient>
            <pattern id="path-mm-constellation" width="28" height="28" patternUnits="userSpaceOnUse">
              <circle cx="4" cy="6" r="0.65" fill="#3d9b84" opacity="0.12" />
              <circle cx="18" cy="14" r="0.5" fill="#b45309" opacity="0.1" />
              <circle cx="24" cy="22" r="0.45" fill="#3d9b84" opacity="0.08" />
            </pattern>
            <filter id="path-mm-soft-shadow" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1c1917" floodOpacity="0.1" />
            </filter>
          </defs>
          <rect x={0} y={0} width={width} height={height} fill={`url(#${gradientId})`} rx={14} />
          <rect x={0} y={0} width={width} height={height} fill="url(#path-mm-constellation)" rx={14} />
          {model.edges.map((edge) => {
            const a = layoutById.get(edge.from);
            const b = layoutById.get(edge.to);
            if (!a || !b) return null;
            const relation = resolveAskGraphEdgeRelation(edge, nodeById);
            const active = activeIds.has(edge.from) || activeIds.has(edge.to);
            const mx = (a.x + b.x) / 2;
            const my = (a.y + b.y) / 2;
            // Friend/a11y: never paint mid-edge 「인용」 spam — legend+CSS keep typed edges honest.
            // Path labels optional; citation/related stay color-only (no empty repeated list text).
            const showMidLabel = paintLabels && relation === "path_sequential";
            const pathIdx = pathEdgeOrder.order.get(`${edge.from}|${edge.to}`);
            const pathCount = pathEdgeOrder.count;
            // Bridge metaphor from path order only — peak weight mid-spine (not real KG betweenness).
            // 2-edge paths: keep calm mid weight (formula collapses to 0 at both ends when n=2).
            const bridgeT =
              relation === "path_sequential" && pathCount > 2 && pathIdx != null
                ? 1 - Math.abs((2 * pathIdx) / (pathCount - 1) - 1)
                : relation === "path_sequential"
                  ? 0.62
                  : 0;
            const pathStrokeW =
              relation === "path_sequential" ? Number((1.65 + bridgeT * 0.85).toFixed(2)) : undefined;
            const midLabelText =
              showMidLabel && pathOrdinalLabels && pathIdx != null
                ? String(pathIdx + 1)
                : showMidLabel
                  ? ASK_GRAPH_EDGE_LABEL_SHORT[relation]
                  : null;
            return (
              <g
                key={`${edge.from}-${edge.to}-${relation}`}
                data-edge-relation={relation}
                data-path-ord={pathIdx != null ? String(pathIdx + 1) : undefined}
                data-path-bridge={relation === "path_sequential" ? bridgeT.toFixed(2) : undefined}
                aria-hidden="true"
              >
                <path
                  d={curvedEdgePath(a.x, a.y, b.x, b.y)}
                  className={`lr-studio-mindmap-edge ${edgeRelationCssClass(relation)}${active ? " lr-studio-mindmap-edge--active" : ""}`}
                  fill="none"
                  style={pathStrokeW != null ? { strokeWidth: pathStrokeW } : undefined}
                />
                {midLabelText ? (
                  <text
                    x={mx}
                    y={my - 5}
                    textAnchor="middle"
                    className={`lr-studio-mindmap-edge-label lr-studio-mindmap-edge-label--${relation}${pathOrdinalLabels ? " lr-studio-mindmap-edge-label--ord" : ""}`}
                    aria-hidden="true"
                  >
                    {midLabelText}
                  </text>
                ) : null}
              </g>
            );
          })}
          {layout
            .filter((node) => node.kind === "mesh")
            .map((node) => {
              const style = kindStyles.mesh || kindStyles.spine;
              const active = activeIds.has(node.id);
              const hubRaw = node.meta?.startsWith("hub:") ? Number(node.meta.slice(4)) : NaN;
              const hubBoost = Number.isFinite(hubRaw) ? 0.35 + hubRaw * 0.9 : 1;
              const r = (style?.r ?? 5) * hubBoost * (active ? 1.15 : 1);
              return (
                <g
                  key={node.id}
                  className={`lr-studio-mindmap-node lr-studio-mindmap-node--mesh${active ? " lr-studio-mindmap-node--active" : ""}`}
                  data-hub-metaphor={Number.isFinite(hubRaw) ? hubRaw.toFixed(2) : undefined}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId((id) => (id === node.id ? null : id))}
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={r}
                    fill={style?.fill ?? "rgba(148,163,184,0.35)"}
                    stroke={style?.stroke ?? "rgba(148,163,184,0.55)"}
                    strokeWidth={active ? 1.8 : 1}
                    opacity={Number.isFinite(hubRaw) ? 0.45 + hubRaw * 0.4 : 0.7}
                  />
                </g>
              );
            })}
          {layout
            .filter((node) => node.kind !== "mesh")
            .map((node) => {
              const style = kindStyles[node.kind] || kindStyles.spine || kindStyles.pillar;
              const active = activeIds.has(node.id);
              const breathe = active ? 1 + 0.08 * Math.sin(pulsePhase * 5) : 1;
              const r = (style?.r ?? 18) * breathe;
              const labelY = node.y + r + 14;
              const isLeaf = leafSet.has(node.kind);
              const clickable = isLeaf && onLeafClick;
              return (
                <g
                  key={node.id}
                  className={`lr-studio-mindmap-node lr-studio-mindmap-node--${node.kind}${active ? " lr-studio-mindmap-node--active" : ""}`}
                  filter="url(#path-mm-soft-shadow)"
                  onClick={() => {
                    if (clickable) onLeafClick(node);
                  }}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId((id) => (id === node.id ? null : id))}
                  style={{ cursor: clickable ? "pointer" : "default" }}
                  aria-label={nodeTooltips?.[node.id] ?? node.label}
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={r}
                    fill={style?.fill ?? "#f5f0e8"}
                    stroke={style?.stroke ?? "#b45309"}
                    strokeWidth={active ? 2.5 : 1.5}
                  />
                  {node.kind === "root" ? (
                    externalRootCaption ? (
                      <text
                        x={node.x}
                        y={node.y + 5}
                        textAnchor="middle"
                        fill={style?.text ?? "#ffffff"}
                        className="lr-studio-mindmap-root-glyph"
                      >
                        Q
                      </text>
                    ) : (
                      <text
                        x={node.x}
                        y={node.y + 4}
                        textAnchor="middle"
                        fill={style?.text ?? "#ffffff"}
                        className="lr-studio-mindmap-root-text"
                      >
                        {summarizeNodeLabel(node)}
                      </text>
                    )
                  ) : (
                    <text
                      x={node.x}
                      y={labelY}
                      textAnchor="middle"
                      className="lr-studio-mindmap-label"
                      fill={style?.text ?? "#292524"}
                      stroke="rgba(255, 255, 255, 0.88)"
                      strokeWidth={3}
                      paintOrder="stroke fill"
                    >
                      <title>{node.label}</title>
                      {summarizeNodeLabel(node)}
                    </text>
                  )}
                </g>
              );
            })}
        </svg>
        {hoveredTooltip ? (
          <div className="lr-studio-mindmap-tooltip" role="tooltip">
            {hoveredTooltip}
          </div>
        ) : null}
      </div>

      <p className="lr-studio-mindmap-foot" role="note">
        {footnote}
      </p>
    </div>
  );
}
