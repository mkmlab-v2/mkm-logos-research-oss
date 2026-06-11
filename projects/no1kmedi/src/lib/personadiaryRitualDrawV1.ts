/**
 * PersonaDiary ritual draw v1 — Major Arcana 22 LUT, session-only [HYPO] preview.
 * B-track: no mkmlife DB merge, no clinical CDSS coupling.
 */

import type { DailyGuidePackage } from "@/lib/personadiaryDailyGuide";

export const BREATH_GATE_DURATION_MS = 3000;
export const RITUAL_LUT_URL = "/data/personadiary_ritual_draw_lut_major22_v1.json";
export const RITUAL_LOG_KEY = "personadiary_ritual_draw_log_v1";
export const RITUAL_DRAW_SESSION_KEY_PREFIX = "pd_ritual_draw_v1_";

export type RitualLutCard = {
  card_id: string;
  name_ko: string;
  name_en: string;
  atom_id: string;
  reflect_prompt_ko: string;
  logos_hint_ko: string;
  sasang_metaphor_ko: string;
};

export type RitualLutDoc = {
  schema: string;
  version: number;
  ritual_mode: string;
  preview_only: boolean;
  disclaimer_ko: string;
  cards: RitualLutCard[];
};

export type RitualDrawLogEntry = {
  schema: "personadiary_ritual_draw_log_v1";
  draw_token: string;
  card_id: string;
  atom_id: string;
  raw_lut_hit: boolean;
  repair_overlay_applied: boolean;
  question_snippet?: string;
  ts: string;
};

export type RitualDrawResult = {
  card: RitualLutCard;
  drawIndex: number;
  drawToken: string;
  raw_lut_hit: true;
  repair_overlay_applied: boolean;
  guide_overlay_ko?: string;
  logos_hint_ko: string;
  sasang_metaphor_ko: string;
};

export function kstDateKey(d = new Date()): string {
  return d.toLocaleDateString("en-CA", { timeZone: "Asia/Seoul" });
}

export function sessionDrawStorageKey(dateKey = kstDateKey()): string {
  return `${RITUAL_DRAW_SESSION_KEY_PREFIX}${dateKey}`;
}

export function randomDrawToken(): string {
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    const buf = new Uint32Array(2);
    crypto.getRandomValues(buf);
    return `${buf[0].toString(16)}${buf[1].toString(16)}`;
  }
  return `${Date.now().toString(16)}${Math.floor(Math.random() * 1e9).toString(16)}`;
}

export function pickDrawIndex(drawToken: string, deckSize: number): number {
  if (deckSize <= 0) return 0;
  let hash = 0;
  for (let i = 0; i < drawToken.length; i++) {
    hash = (hash * 31 + drawToken.charCodeAt(i)) >>> 0;
  }
  return hash % deckSize;
}

export function resolveLutCard(lut: RitualLutDoc, drawToken: string): RitualDrawResult | null {
  const cards = lut.cards ?? [];
  if (!cards.length) return null;
  const drawIndex = pickDrawIndex(drawToken, cards.length);
  const card = cards[drawIndex];
  if (!card?.card_id) return null;
  return {
    card,
    drawIndex,
    drawToken,
    raw_lut_hit: true,
    repair_overlay_applied: false,
    logos_hint_ko: card.logos_hint_ko,
    sasang_metaphor_ko: card.sasang_metaphor_ko,
  };
}

export function pickGuideOverlayKo(
  pkg: DailyGuidePackage | null | undefined,
  drawIndex: number
): string | undefined {
  const blocks =
    pkg?.ui_blocks?.filter(
      (b) =>
        b.type === "card" ||
        b.type === "verse" ||
        b.type === "world_pulse" ||
        b.type === "user_condition"
    ) ?? [];
  if (!blocks.length) return undefined;
  const block = blocks[drawIndex % blocks.length];
  const line = block.body_ko?.split("\n").map((s) => s.trim()).find(Boolean);
  return line?.slice(0, 160);
}

export function applyGuideOverlay(
  result: RitualDrawResult,
  pkg: DailyGuidePackage | null | undefined
): RitualDrawResult {
  const overlay = pickGuideOverlayKo(pkg, result.drawIndex);
  if (!overlay) return result;
  return {
    ...result,
    repair_overlay_applied: true,
    guide_overlay_ko: overlay,
  };
}

export function buildMkmlifeHandoffUrl(
  question: string,
  cardName?: string,
  opts?: { anchor?: string; demo?: string },
): string {
  const q = question.trim();
  const prefill = cardName && q ? `[${cardName}] ${q}` : q || cardName || "";
  const params = new URLSearchParams();
  if (prefill) params.set("prefill", prefill.slice(0, 500));
  params.set("source", "personadiary_ritual_v1");
  const demo = opts?.demo?.trim();
  const anchor = opts?.anchor?.trim();
  if (demo === "kangmin_growth" || demo === "kangmin") {
    params.set("demo", "kangmin_growth");
  } else if (anchor === "family_anchor_son_kangmin_v1") {
    params.set("anchor", anchor);
  }
  return `https://mkmlife.com/ask-one?${params.toString()}`;
}

export function appendRitualDrawLog(entry: RitualDrawLogEntry): void {
  if (typeof window === "undefined") return;
  try {
    const raw = window.sessionStorage.getItem(RITUAL_LOG_KEY);
    const list: RitualDrawLogEntry[] = raw ? (JSON.parse(raw) as RitualDrawLogEntry[]) : [];
    list.push(entry);
    const trimmed = list.slice(-20);
    window.sessionStorage.setItem(RITUAL_LOG_KEY, JSON.stringify(trimmed));
  } catch {
    /* session-only best effort */
  }
}

export function persistSessionDraw(result: RitualDrawResult, question: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(
      sessionDrawStorageKey(),
      JSON.stringify({
        card_id: result.card.card_id,
        draw_token: result.drawToken,
        question: question.slice(0, 280),
        ts: new Date().toISOString(),
      })
    );
  } catch {
    /* ignore */
  }
}

export function loadSessionDraw(): {
  card_id: string;
  draw_token: string;
  question: string;
} | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(sessionDrawStorageKey());
    if (!raw) return null;
    return JSON.parse(raw) as { card_id: string; draw_token: string; question: string };
  } catch {
    return null;
  }
}

export async function fetchRitualLut(): Promise<RitualLutDoc | null> {
  const res = await fetch(RITUAL_LUT_URL, { cache: "no-store" });
  if (!res.ok) return null;
  const doc = (await res.json()) as RitualLutDoc;
  if (doc.schema !== "personadiary_ritual_draw_lut_major22_v1") return null;
  return doc;
}
