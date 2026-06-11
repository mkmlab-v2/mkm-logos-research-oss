/**
 * PersonaDiary Lattice Convergence v1 — shatter → vortex → breath → hub rank → encapsulate.
 * B-track [HYPO]: session-only, static bloom slice, no remote DB / mkmlife merge.
 */

export const LATTICE_SESSION_SCHEMA = "personadiary_lattice_convergence_session_v1" as const;
export const LATTICE_BLOOM_SLICE_URL =
  "/data/personadiary_lattice_convergence_bloom_slice_v1.json";
export const LATTICE_SESSION_KEY = "personadiary_lattice_convergence_session_v1";

export const LATTICE_SHATTER_MS = 1200;
export const LATTICE_VORTEX_MS = 1800;
export const LATTICE_BREATH_MS = 3000;
export const LATTICE_CONVERGE_MS = 800;
export const SHATTER_PARTICLES_MAX = 24;
export const MINI_BLOOM_HUB_CAP = 5;

export type LatticePhase =
  | "idle"
  | "shatter"
  | "vortex"
  | "breath"
  | "ready"
  | "converge"
  | "encapsulate"
  | "done";

export type BloomNodeKind =
  | "query"
  | "verse"
  | "theme"
  | "regime"
  | "concept"
  | "lemma"
  | "other";

export type BloomSliceNode = {
  id: string;
  label: string;
  label_ko?: string;
  kind: BloomNodeKind;
  hub_score?: number;
  ref?: string;
  corpus?: string;
};

export type BloomSliceDoc = {
  schema: "magic_orb_graph_bloom_v1";
  nodes: BloomSliceNode[];
  edges?: Array<{ src: string; dst: string; weight?: number }>;
  disclaimer_ko?: string;
  research_only?: boolean;
  non_gating?: boolean;
};

export type MatchedHub = {
  id: string;
  label_ko: string;
  kind: BloomNodeKind;
  score: number;
  jaccard: number;
};

export type LatticeSessionRecord = {
  schema: typeof LATTICE_SESSION_SCHEMA;
  version: 1;
  phase: LatticePhase;
  question_snippet?: string;
  shatter_tokens?: string[];
  matched_hub_ids?: string[];
  matched_hub_labels_ko?: string[];
  bloom_slice_url: string;
  draw_token?: string;
  encapsulation_card_id?: string;
  preview_only: true;
  research_only: true;
  session_storage_only: true;
  hypothesis_tier: "B";
  non_gating: true;
  disclaimer_ko: string;
  ts: string;
};

export const LATTICE_DISCLAIMER_KO =
  "[가설] 공명 맵·성찰 프리뷰입니다. 투자·실매매·의료·처방·Track A 압축 공식 근거가 아닙니다.";

/** Lightweight shatter — whitespace/punctuation split, no morph analyzer. */
export function shatterQuestionTokens(question: string, max = SHATTER_PARTICLES_MAX): string[] {
  const q = question.trim();
  if (!q) return [];
  const out: string[] = [];
  const chunks = q.split(/[\s,?.!;:·…、，。！？]+/).filter(Boolean);
  for (const chunk of chunks) {
    if (out.length >= max) break;
    if (chunk.length <= 4) {
      out.push(chunk);
      continue;
    }
    out.push(chunk.slice(0, 4));
    if (out.length < max && chunk.length > 4) {
      out.push(chunk.slice(-2));
    }
  }
  return out.slice(0, max);
}

function tokenSet(text: string, max = 64): Set<string> {
  return new Set(
    shatterQuestionTokens(text, max).map((t) => t.trim().toLowerCase()).filter(Boolean)
  );
}

export function jaccardSimilarity(a: Set<string>, b: Set<string>): number {
  if (!a.size && !b.size) return 0;
  let inter = 0;
  for (const x of a) {
    if (b.has(x)) inter += 1;
  }
  const union = a.size + b.size - inter;
  return union ? inter / union : 0;
}

export function bloomNodeLabelKo(node: BloomSliceNode): string {
  return (node.label_ko || node.label || node.id).trim();
}

/** Rank hubs by Jaccard(question, label) blended with static hub_score. */
export function rankBloomHubs(
  question: string,
  bloom: BloomSliceDoc,
  cap = MINI_BLOOM_HUB_CAP
): MatchedHub[] {
  const qTokens = tokenSet(question);
  const candidates = (bloom.nodes ?? []).filter((n) => n.kind !== "query" && n.id);
  const scored = candidates.map((node) => {
    const label = bloomNodeLabelKo(node);
    const nTokens = tokenSet(label);
    const jac = jaccardSimilarity(qTokens, nTokens);
    const hub = typeof node.hub_score === "number" ? node.hub_score : 0.5;
    const score = jac * 0.6 + hub * 0.4;
    return { id: node.id, label_ko: label, kind: node.kind, score, jaccard: jac };
  });
  scored.sort((a, b) => b.score - a.score || b.jaccard - a.jaccard);
  return scored.slice(0, cap);
}

export function latticePhaseDurationMs(phase: LatticePhase): number {
  switch (phase) {
    case "shatter":
      return LATTICE_SHATTER_MS;
    case "vortex":
      return LATTICE_VORTEX_MS;
    case "breath":
      return LATTICE_BREATH_MS;
    case "converge":
      return LATTICE_CONVERGE_MS;
    default:
      return 0;
  }
}

export function nextLatticePhase(phase: LatticePhase): LatticePhase | null {
  const order: LatticePhase[] = [
    "idle",
    "shatter",
    "vortex",
    "breath",
    "ready",
    "converge",
    "encapsulate",
    "done",
  ];
  const i = order.indexOf(phase);
  if (i < 0 || i >= order.length - 1) return null;
  return order[i + 1];
}

export function buildLatticeSession(
  partial: Pick<
    LatticeSessionRecord,
    "phase" | "question_snippet" | "shatter_tokens" | "matched_hub_ids" | "matched_hub_labels_ko"
  > & {
    draw_token?: string;
    encapsulation_card_id?: string;
  }
): LatticeSessionRecord {
  return {
    schema: LATTICE_SESSION_SCHEMA,
    version: 1,
    bloom_slice_url: LATTICE_BLOOM_SLICE_URL,
    preview_only: true,
    research_only: true,
    session_storage_only: true,
    hypothesis_tier: "B",
    non_gating: true,
    disclaimer_ko: LATTICE_DISCLAIMER_KO,
    ts: new Date().toISOString(),
    ...partial,
  };
}

export function persistLatticeSession(record: LatticeSessionRecord): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(LATTICE_SESSION_KEY, JSON.stringify(record));
  } catch {
    /* session-only */
  }
}

export function loadLatticeSession(): LatticeSessionRecord | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(LATTICE_SESSION_KEY);
    if (!raw) return null;
    const doc = JSON.parse(raw) as LatticeSessionRecord;
    if (doc.schema !== LATTICE_SESSION_SCHEMA) return null;
    return doc;
  } catch {
    return null;
  }
}

export async function fetchLatticeBloomSlice(): Promise<BloomSliceDoc | null> {
  const res = await fetch(LATTICE_BLOOM_SLICE_URL, { cache: "no-store" });
  if (!res.ok) return null;
  const doc = (await res.json()) as BloomSliceDoc;
  if (doc.schema !== "magic_orb_graph_bloom_v1" || !Array.isArray(doc.nodes)) return null;
  return doc;
}

export type ShatterParticle = {
  token: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
};

/** Initial positions around orb perimeter for canvas overlay. */
export function initShatterParticles(
  tokens: string[],
  centerX: number,
  centerY: number,
  radius: number
): ShatterParticle[] {
  return tokens.map((token, i) => {
    const angle = (i / Math.max(1, tokens.length)) * Math.PI * 2 + Math.random() * 0.4;
    const r = radius * (0.85 + Math.random() * 0.35);
    const x = centerX + Math.cos(angle) * r;
    const y = centerY + Math.sin(angle) * r;
    const dx = centerX - x;
    const dy = centerY - y;
    const dist = Math.hypot(dx, dy) || 1;
    return {
      token,
      x,
      y,
      vx: (dx / dist) * (0.4 + Math.random() * 0.3),
      vy: (dy / dist) * (0.4 + Math.random() * 0.3),
      life: 1,
    };
  });
}

export function stepShatterParticles(
  particles: ShatterParticle[],
  centerX: number,
  centerY: number,
  mode: "shatter" | "vortex"
): ShatterParticle[] {
  const swirl = mode === "vortex" ? 0.08 : 0.02;
  return particles
    .map((p) => {
      const dx = centerX - p.x;
      const dy = centerY - p.y;
      const dist = Math.hypot(dx, dy) || 1;
      const ax = (dx / dist) * (mode === "vortex" ? 0.35 : 0.15);
      const ay = (dy / dist) * (mode === "vortex" ? 0.35 : 0.15);
      const tx = -dy / dist;
      const ty = dx / dist;
      return {
        ...p,
        vx: p.vx + ax + tx * swirl,
        vy: p.vy + ay + ty * swirl,
        x: p.x + p.vx,
        y: p.y + p.vy,
        life: Math.max(0, p.life - (mode === "vortex" ? 0.018 : 0.006)),
      };
    })
    .filter((p) => p.life > 0.05 && Math.hypot(p.x - centerX, p.y - centerY) > 8);
}
