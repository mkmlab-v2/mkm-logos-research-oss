/**
 * D-VIZ-4 — Ask text↔graph braid L0 (research_only · [NON_GATING]).
 * Only maps citation-lock / S1 verse refs that already exist on the path mindmap.
 * Never invents mesh edges or softmatch aliases.
 */

import { normalizeRefKey } from "@/lib/logosResearchHighlightV1";
import {
  mindmapNodeIdsForVerseRef,
  type PathMindmapModel,
} from "@/lib/logosResearchPathMindmapV1";

export type BraidEssayToken =
  | { type: "text"; value: string }
  | { type: "ref"; value: string; canonical: string };

export function braidRefsEqual(a: string, b: string): boolean {
  return normalizeRefKey(a).toLowerCase() === normalizeRefKey(b).toLowerCase();
}

/** Toggle: same ref again clears focus. */
export function nextBraidFocus(current: string | null, clicked: string): string | null {
  const t = String(clicked || "").trim();
  if (!t) return current;
  if (current && braidRefsEqual(current, t)) return null;
  return t;
}

/**
 * Honest resolve: only return a focus if it matches a known citation-lock / path ref.
 * Unknown strings → null (no fake graph hit).
 */
export function resolveBraidFocusRef(
  candidate: string | null | undefined,
  knownRefs: string[],
): string | null {
  const c = String(candidate || "").trim();
  if (!c || !knownRefs.length) return null;
  const hit = knownRefs.find((r) => braidRefsEqual(r, c));
  return hit ?? null;
}

export function braidActiveNodeIds(
  focusRef: string | null,
  model: PathMindmapModel,
): string[] {
  if (!focusRef) return [];
  const direct = mindmapNodeIdsForVerseRef(focusRef, model);
  if (direct.length) return direct;
  // Fallback: case-insensitive label match (still only existing mindmap nodes).
  const key = normalizeRefKey(focusRef).toLowerCase();
  return model.nodes
    .filter((n) => normalizeRefKey(n.label).toLowerCase() === key)
    .map((n) => n.id);
}

export function braidHasGraphHit(focusRef: string | null, model: PathMindmapModel): boolean {
  return braidActiveNodeIds(focusRef, model).length > 0;
}

/** Incident edges of focused verse nodes — real model edges only. */
export function braidIncidentEdgeKeys(
  focusRef: string | null,
  model: PathMindmapModel,
): string[] {
  const ids = new Set(braidActiveNodeIds(focusRef, model));
  if (!ids.size) return [];
  const keys: string[] = [];
  for (const e of model.edges) {
    if (ids.has(e.from) || ids.has(e.to)) {
      keys.push(`${e.from}->${e.to}`);
    }
  }
  return keys;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Split essay text so only *known* verse refs become clickable tokens.
 * Does not invent refs that are absent from citation lock / path.
 */
export function splitEssayByKnownRefs(text: string, knownRefs: string[]): BraidEssayToken[] {
  const body = String(text || "");
  if (!body || !knownRefs.length) return [{ type: "text", value: body }];

  const uniq: string[] = [];
  const seen = new Set<string>();
  for (const r of knownRefs) {
    const t = String(r || "").trim();
    if (!t) continue;
    const k = normalizeRefKey(t).toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    uniq.push(t);
  }
  uniq.sort((a, b) => b.length - a.length);
  if (!uniq.length) return [{ type: "text", value: body }];

  const pattern = uniq.map(escapeRegExp).join("|");
  const re = new RegExp(`(${pattern})`, "gi");
  const out: BraidEssayToken[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(body)) !== null) {
    const start = m.index;
    const raw = m[0];
    if (start > last) {
      out.push({ type: "text", value: body.slice(last, start) });
    }
    const canonical = resolveBraidFocusRef(raw, uniq) ?? raw;
    out.push({ type: "ref", value: raw, canonical });
    last = start + raw.length;
  }
  if (last < body.length) {
    out.push({ type: "text", value: body.slice(last) });
  }
  return out.length ? out : [{ type: "text", value: body }];
}
