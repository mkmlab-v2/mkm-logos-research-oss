/** Shared radial path mindmap layout (lens-agnostic · research_only · [HYPO]). */

export type MindmapNode = {
  id: string;
  label: string;
  kind: string;
  depth: number;
  parentId?: string;
  graphNodeId?: string;
  meta?: string;
};

export type MindmapEdge = {
  from: string;
  to: string;
};

export type PathMindmapModel = {
  nodes: MindmapNode[];
  edges: MindmapEdge[];
  rootId: string;
};

export type MindmapLayoutNode = MindmapNode & {
  x: number;
  y: number;
  angle: number;
};

export type LayoutPathMindmapOptions = {
  leafKinds?: string[];
  presetId?: string;
};

/** Fixed spine angles (deg, 0=right, -90=top) — Job spine Figma v1 PoC */
export const PRESET_SPINE_ANGLE_DEG_V1: Record<string, number[]> = {
  job_job_suffering_reason: [-90, 12, 128, 210, 288, 36],
};

export function truncateMindmapLabel(text: string, max: number): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

export function layoutPathMindmapRadial(
  model: PathMindmapModel,
  width: number,
  height: number,
  opts?: LayoutPathMindmapOptions,
): MindmapLayoutNode[] {
  const leafKinds = opts?.leafKinds ?? ["verse"];
  const isLeaf = (kind: string) => leafKinds.includes(kind);

  const cx = width / 2;
  const cy = height / 2;
  const base = Math.min(width, height);
  const r1 = base * 0.24;
  const r2 = base * 0.42;

  const pos = new Map<string, { x: number; y: number; angle: number }>();
  pos.set(model.rootId, { x: cx, y: cy, angle: -Math.PI / 2 });

  const spine = model.nodes.filter((n) => n.depth === 1 && !isLeaf(n.kind));
  const count = Math.max(spine.length, 1);
  const presetAngles = opts?.presetId ? PRESET_SPINE_ANGLE_DEG_V1[opts.presetId] : undefined;
  spine.forEach((node, i) => {
    const angleDeg = presetAngles?.[i % (presetAngles.length || 1)];
    const angle =
      angleDeg !== undefined
        ? (angleDeg * Math.PI) / 180
        : (2 * Math.PI * i) / count - Math.PI / 2;
    pos.set(node.id, {
      x: cx + r1 * Math.cos(angle),
      y: cy + r1 * Math.sin(angle),
      angle,
    });
  });

  const leaves = model.nodes.filter((n) => isLeaf(n.kind));
  const byParent = new Map<string, MindmapNode[]>();
  for (const leaf of leaves) {
    const pid = leaf.parentId || model.rootId;
    const arr = byParent.get(pid) || [];
    arr.push(leaf);
    byParent.set(pid, arr);
  }

  for (const [parentId, group] of byParent) {
    const parentPos = pos.get(parentId) || { x: cx, y: cy, angle: -Math.PI / 2 };
    const gCount = group.length;
    group.forEach((leaf, i) => {
      const spread = Math.min(0.55, 0.18 * gCount);
      const offset = gCount === 1 ? 0 : -spread / 2 + (spread * i) / (gCount - 1);
      const angle = parentPos.angle + offset;
      pos.set(leaf.id, {
        x: cx + r2 * Math.cos(angle),
        y: cy + r2 * Math.sin(angle),
        angle,
      });
    });
  }

  const mesh = model.nodes.filter((n) => n.kind === "mesh");
  const r3 = base * 0.52;
  mesh.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(mesh.length, 1) - Math.PI / 2;
    pos.set(node.id, {
      x: cx + r3 * Math.cos(angle),
      y: cy + r3 * Math.sin(angle),
      angle,
    });
  });

  return model.nodes.map((node) => {
    const p = pos.get(node.id) || { x: cx, y: cy, angle: 0 };
    return { ...node, ...p };
  });
}

export function mindmapNodeIdsForGraphPulse(
  graphNodeIds: string[],
  model: PathMindmapModel,
): string[] {
  const out = new Set<string>();
  for (const gid of graphNodeIds) {
    for (const n of model.nodes) {
      if (n.graphNodeId === gid) out.add(n.id);
    }
    const tail = gid.split("::").pop() || "";
    for (const n of model.nodes) {
      if (n.label.replace(/\s+/g, "") === tail.replace(/\s+/g, "")) out.add(n.id);
    }
  }
  return [...out];
}

export function mindmapNodeIdsForLabelMatch(ref: string, model: PathMindmapModel): string[] {
  const key = ref.replace(/\s+/g, "");
  const hit = model.nodes.find((n) => n.label.replace(/\s+/g, "") === key);
  return hit ? [hit.id] : [];
}

export function curvedEdgePath(x1: number, y1: number, x2: number, y2: number): string {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const cx = mx - dy * 0.15;
  const cy = my + dx * 0.15;
  return `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
}
