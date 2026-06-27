import type { LogosGraphSliceNode } from "./logosResearchHighlightV1";

export type FrozenNodePosition = {
  id: string;
  x: number;
  y: number;
};

/** Deterministic seed so force layout starts stable (circular). */
export function seedCircularPositions(
  nodes: LogosGraphSliceNode[],
  radius = 260,
): FrozenNodePosition[] {
  const count = Math.max(nodes.length, 1);
  return nodes.map((node, index) => {
    const angle = (2 * Math.PI * index) / count - Math.PI / 2;
    const hubBoost = (node.hub_score || 0) * 18;
    const r = radius - hubBoost;
    return {
      id: node.id,
      x: Math.cos(angle) * r,
      y: Math.sin(angle) * r,
    };
  });
}

const KIND_RING_RADIUS: Record<string, number> = {
  verse: 95,
  theme: 175,
  regime: 245,
  stage: 285,
  other: 265,
};

/** Kind rings + spine arc — readable topology without force jitter. */
export function seedTopologyLayout(
  nodes: LogosGraphSliceNode[],
  pathSpineIds: string[] = [],
  highlightIds: string[] = [],
): FrozenNodePosition[] {
  const spineSet = new Set(pathSpineIds.filter(Boolean));
  const highlightSet = new Set(highlightIds.filter(Boolean));
  const positions = new Map<string, FrozenNodePosition>();
  const spine = pathSpineIds.filter((id) => nodes.some((n) => n.id === id));

  if (spine.length) {
    const arcSpan =
      spine.length > 1 ? Math.min(Math.PI * 1.22, (spine.length - 1) * 0.68) : 0;
    const start = -Math.PI / 2 - arcSpan / 2;
    const spineRadius = 102;
    spine.forEach((id, index) => {
      const angle = spine.length === 1 ? -Math.PI / 2 : start + index * arcSpan;
      const kind = nodes.find((n) => n.id === id)?.kind || "other";
      const kindRadius =
        kind === "theme" ? spineRadius + 8 : kind === "verse" ? spineRadius - 6 : spineRadius;
      positions.set(id, {
        id,
        x: Math.cos(angle) * kindRadius,
        y: Math.sin(angle) * kindRadius,
      });
    });
  }

  const highlightOnly = highlightIds.filter(
    (id) => highlightSet.has(id) && !spineSet.has(id) && nodes.some((n) => n.id === id),
  );
  if (highlightOnly.length) {
    const arcSpan = highlightOnly.length > 1 ? Math.PI * 0.78 : 0;
    const start = Math.PI / 2 - arcSpan / 2;
    const hlRadius = 128;
    highlightOnly.forEach((id, index) => {
      const angle = highlightOnly.length === 1 ? Math.PI / 2 + 0.42 : start + index * arcSpan;
      positions.set(id, {
        id,
        x: Math.cos(angle) * hlRadius,
        y: Math.sin(angle) * hlRadius,
      });
    });
  }

  const byKind: Record<string, LogosGraphSliceNode[]> = {};
  for (const node of nodes) {
    if (spineSet.has(node.id) || highlightSet.has(node.id)) continue;
    const kind = node.kind || "other";
    (byKind[kind] ||= []).push(node);
  }

  for (const [kind, group] of Object.entries(byKind)) {
    const baseR = KIND_RING_RADIUS[kind] ?? 265;
    const count = Math.max(group.length, 1);
    group.forEach((node, index) => {
      const phase = (kind.charCodeAt(0) % 7) * 0.09;
      const angle = (2 * Math.PI * index) / count - Math.PI / 2 + phase;
      const hubPull = (node.hub_score || 0) * 14;
      const r = Math.max(48, baseR - hubPull);
      positions.set(node.id, {
        id: node.id,
        x: Math.cos(angle) * r,
        y: Math.sin(angle) * r,
      });
    });
  }

  for (const node of nodes) {
    if (!positions.has(node.id)) {
      positions.set(node.id, { id: node.id, x: 0, y: 0 });
    }
  }

  return Array.from(positions.values());
}

export function positionsToRecord(positions: FrozenNodePosition[]): Record<string, [number, number]> {
  const map: Record<string, [number, number]> = {};
  for (const p of positions) map[p.id] = [p.x, p.y];
  return map;
}

export function recordToPositions(map: Record<string, [number, number]>): FrozenNodePosition[] {
  return Object.entries(map).map(([id, [x, y]]) => ({ id, x, y }));
}
