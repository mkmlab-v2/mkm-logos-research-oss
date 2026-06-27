/** Layer B 30s demo beat SSOT — sync with marketing-site/logos-research-copy.json graph_studio.demo_steps */

export type LogosStoryboardSlotId = "field" | "lens" | "conflict" | "gap" | "final";

export type LogosHeroDemoBeat = {
  id: string;
  slot: LogosStoryboardSlotId;
  startMs: number;
  endMs: number;
  labelKo: string;
};

export const LOGOS_HERO_DEMO_BEATS_V1: LogosHeroDemoBeat[] = [
  {
    id: "0-8s_preset_load",
    slot: "field",
    startMs: 0,
    endMs: 8000,
    labelKo: "프리셋 로드 — Field",
  },
  {
    id: "8-18s_path_refs",
    slot: "lens",
    startMs: 8000,
    endMs: 18000,
    labelKo: "Path · ECS — Lens",
  },
  {
    id: "18-22s_conflict",
    slot: "conflict",
    startMs: 18000,
    endMs: 22000,
    labelKo: "학파 격벽 — Conflict",
  },
  {
    id: "22-26s_gap",
    slot: "gap",
    startMs: 22000,
    endMs: 26000,
    labelKo: "구조적 Gap",
  },
  {
    id: "26-30s_verdict",
    slot: "final",
    startMs: 26000,
    endMs: 30000,
    labelKo: "한 줄 통찰 · logos.jema-ai.com",
  },
];

export const LOGOS_HERO_DEMO_LOOP_MS = 30000;

export function beatAtElapsedMs(elapsedMs: number): LogosHeroDemoBeat {
  const t = ((elapsedMs % LOGOS_HERO_DEMO_LOOP_MS) + LOGOS_HERO_DEMO_LOOP_MS) % LOGOS_HERO_DEMO_LOOP_MS;
  for (let i = LOGOS_HERO_DEMO_BEATS_V1.length - 1; i >= 0; i--) {
    if (t >= LOGOS_HERO_DEMO_BEATS_V1[i].startMs) return LOGOS_HERO_DEMO_BEATS_V1[i];
  }
  return LOGOS_HERO_DEMO_BEATS_V1[0];
}

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
