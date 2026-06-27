/**
 * PersonaDiary Reasoning Theatre v1 — ritual phase → artifact-bound step mapping.
 * Slim parity with mkmlife magic-orb-reasoning-theatre (no cross-package import).
 */

import type { LatticePhase } from "@/lib/personadiaryLatticeConvergenceV1";

export type PdReasoningTheatreStepId =
  | "ingest"
  | "field"
  | "retrieve"
  | "lens_logos"
  | "conflict"
  | "bloom"
  | "resolve";

export type PdReasoningTheatreStep = {
  id: PdReasoningTheatreStepId;
  label_ko: string;
  depth: number;
  orbit_hue: number;
};

export const MKMLIFE_THEATRE_API_ORIGIN =
  (typeof process !== "undefined" &&
    process.env.NEXT_PUBLIC_MKMLIFE_API_ORIGIN?.replace(/\/$/, "")) ||
  "https://mkmlife.com";

const PD_STEP_IDS: PdReasoningTheatreStepId[] = [
  "ingest",
  "field",
  "retrieve",
  "lens_logos",
  "conflict",
  "bloom",
  "resolve",
];

export const PD_REASONING_THEATRE_STEPS: PdReasoningTheatreStep[] = [
  { id: "ingest", label_ko: "질문 흡수", depth: 0.14, orbit_hue: 270 },
  { id: "field", label_ko: "호흡 · 정렬", depth: 0.32, orbit_hue: 248 },
  { id: "retrieve", label_ko: "말 조각 수렴", depth: 0.44, orbit_hue: 210 },
  { id: "lens_logos", label_ko: "말씀 · 주제", depth: 0.58, orbit_hue: 195 },
  { id: "conflict", label_ko: "공명 조율", depth: 0.72, orbit_hue: 300 },
  { id: "bloom", label_ko: "공명 맵", depth: 0.86, orbit_hue: 175 },
  { id: "resolve", label_ko: "카드 준비", depth: 0.96, orbit_hue: 220 },
];

function isPdStepId(value: unknown): value is PdReasoningTheatreStepId {
  return typeof value === "string" && PD_STEP_IDS.includes(value as PdReasoningTheatreStepId);
}

function mapMkmlifeTheatreSteps(raw: unknown): PdReasoningTheatreStep[] | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const steps = (raw as { steps?: unknown[] }).steps;
  if (!Array.isArray(steps) || steps.length < 4) return null;
  const mapped: PdReasoningTheatreStep[] = [];
  for (const row of steps) {
    if (!row || typeof row !== "object") continue;
    const item = row as Record<string, unknown>;
    if (!isPdStepId(item.id)) continue;
    mapped.push({
      id: item.id,
      label_ko: typeof item.label_ko === "string" ? item.label_ko : item.id,
      depth: typeof item.depth === "number" ? item.depth : 0.5,
      orbit_hue: typeof item.orbit_hue === "number" ? item.orbit_hue : 220,
    });
  }
  return mapped.length >= 4 ? mapped : null;
}

/** Optional mkmlife insight embed — labels only; phase→step mapping stays local. */
export async function fetchMkmlifeReasoningTheatreSteps(
  query: string,
  baseUrl: string = MKMLIFE_THEATRE_API_ORIGIN,
): Promise<PdReasoningTheatreStep[] | null> {
  const q = query.trim();
  if (!q || typeof fetch === "undefined") return null;
  const origin = baseUrl.replace(/\/$/, "");
  const url = `${origin}/api/v1/magic-orb/insight?query=${encodeURIComponent(q)}`;
  try {
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(12_000),
    });
    if (!res.ok) return null;
    const json = (await res.json()) as {
      reasoning_theatre_v1?: unknown;
      payload?: { reasoning_theatre_v1?: unknown };
    };
    return (
      mapMkmlifeTheatreSteps(json.reasoning_theatre_v1) ??
      mapMkmlifeTheatreSteps(json.payload?.reasoning_theatre_v1)
    );
  } catch {
    return null;
  }
}

export function personadiaryPhaseToTheatreStep(
  phase: LatticePhase,
): PdReasoningTheatreStepId | null {
  switch (phase) {
    case "shatter":
      return "ingest";
    case "vortex":
      return "retrieve";
    case "breath":
      return "field";
    case "converge":
      return "bloom";
    case "encapsulate":
    case "ready":
    case "done":
      return "resolve";
    default:
      return null;
  }
}

export function hueToRgb(h: number, alpha = 1): string {
  const s = 72;
  const l = 62;
  const a = (s * Math.min(l, 100 - l)) / 100;
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color);
  };
  return `rgba(${f(0)}, ${f(8)}, ${f(4)}, ${alpha})`;
}

const STEP_FREQ: Record<PdReasoningTheatreStepId, number> = {
  ingest: 174,
  field: 196,
  retrieve: 220,
  lens_logos: 246.94,
  conflict: 311.13,
  bloom: 329.63,
  resolve: 349.23,
};

export async function playPdReasoningTheatreStepTone(
  stepId: PdReasoningTheatreStepId,
  enabled: boolean,
): Promise<void> {
  if (!enabled || typeof window === "undefined") return;
  const Ctx =
    window.AudioContext ||
    (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctx) return;
  const ctx = new Ctx();
  if (ctx.state === "suspended") await ctx.resume();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.value = STEP_FREQ[stepId] ?? 220;
  gain.gain.value = 0.0001;
  osc.connect(gain);
  gain.connect(ctx.destination);
  const t = ctx.currentTime;
  osc.start(t);
  gain.gain.exponentialRampToValueAtTime(0.035, t + 0.1);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.5);
  osc.stop(t + 0.55);
  window.setTimeout(() => void ctx.close(), 700);
}
