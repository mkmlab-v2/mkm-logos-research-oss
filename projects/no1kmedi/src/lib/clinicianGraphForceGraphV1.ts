import type { GraphBundleV1, GraphEdge, GraphNode } from "./clinicianGraphTypesV1";

export type ClinicianForceGraphNode = {
  id: string;
  name: string;
  kind: string;
  non_gating?: boolean;
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
};

export type ClinicianForceGraphLink = {
  source: string;
  target: string;
  relation: GraphEdge["relation"];
};

export type ClinicianForceGraphData = {
  nodes: ClinicianForceGraphNode[];
  links: ClinicianForceGraphLink[];
};

const KIND_COLOR: Record<string, string> = {
  anchor: "#64748b",
  symptom: "#0ea5e9",
  pattern_hypothesis: "#8b5cf6",
  sasang_hint: "#f59e0b",
  plan_candidate: "#22c55e",
  red_flag: "#ef4444",
  bundle_slot: "#14b8a6",
};

function seedLayout(nodes: GraphNode[]): Map<string, { x: number; y: number }> {
  const pos = new Map<string, { x: number; y: number }>();
  const anchor = nodes.find((n) => n.kind === "anchor");
  if (anchor) pos.set(anchor.id, { x: 0, y: 0 });
  const rest = nodes.filter((n) => n.id !== anchor?.id);
  const radius = 120 + rest.length * 8;
  rest.forEach((node, idx) => {
    const angle = (idx / Math.max(rest.length, 1)) * Math.PI * 2 - Math.PI / 2;
    pos.set(node.id, {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    });
  });
  return pos;
}

export function buildClinicianForceGraphData(bundle: GraphBundleV1): ClinicianForceGraphData {
  const layout = seedLayout(bundle.nodes);
  const nodes: ClinicianForceGraphNode[] = bundle.nodes.map((node) => {
    const p = layout.get(node.id) || { x: 0, y: 0 };
    const label = node.label.length > 28 ? `${node.label.slice(0, 28)}…` : node.label;
    return {
      id: node.id,
      name: label,
      kind: node.kind,
      non_gating: node.non_gating,
      x: p.x,
      y: p.y,
      fx: p.x,
      fy: p.y,
    };
  });
  const links: ClinicianForceGraphLink[] = bundle.edges.map((edge) => ({
    source: edge.from,
    target: edge.to,
    relation: edge.relation,
  }));
  return { nodes, links };
}

export function clinicianNodeColor(node: ClinicianForceGraphNode): string {
  if (node.non_gating) return "#d97706";
  return KIND_COLOR[node.kind] || "#94a3b8";
}

export function clinicianNodeRadius(node: ClinicianForceGraphNode, selectedId?: string): number {
  const base = node.kind === "anchor" ? 7 : node.kind === "red_flag" ? 8 : 6;
  return node.id === selectedId ? base + 3 : base;
}

export function clinicianLinkColor(link: ClinicianForceGraphLink): string {
  if (link.relation === "conflicts") return "#ef4444";
  if (link.relation === "caution") return "#f97316";
  if (link.relation === "supports") return "#22c55e";
  return "#cbd5e1";
}

export function clinicianLinkWidth(link: ClinicianForceGraphLink): number {
  if (link.relation === "caution" || link.relation === "conflicts") return 2.2;
  return 1.2;
}
