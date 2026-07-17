/**
 * Logos Ask theme-fourbin display sidecar (research_only · [HYPO] · NON_GATING).
 * Sibling of graph sidecar — no gematria / vector_4d / address_book merge.
 * Mainline Ask: fixture verse match OR live score from embedded frames lexicon.
 */

import {
  scoreThemeFourbinDisplayLive,
  type ThemeFourbinFramesLexV1,
} from "@/lib/logosAskThemeFourbinScoreV1";

export const THEME_FOURBIN_ASK_DISPLAY_URL =
  "/data/logos_studio/theme_fourbin_ask_display_v1.json";
export const THEME_FOURBIN_ASK_DISPLAY_V = "2026-07-16-ask-mainline-v1";

export const THEME_FOURBIN_LAYOUT_SLOT = "theme_fourbin_display_sidecar";
export const THEME_FOURBIN_SIBLING_OF = "report_split_graph_sidecar";
/** Path-panel tab id for theme meaning-net (separate from graph/address path). */
export const THEME_FOURBIN_PATH_TAB = "theme_meaning_net";
export const THEME_FOURBIN_GRAPH_PATH_TAB = "graph_address_path";

const FORBIDDEN_FIELD_KEYS = new Set([
  "gematria_vector",
  "gematria_slkm",
  "fused_theme_gematria_score",
  "vector_4d",
  "slkm",
]);

export type ThemeFourbinFrameDisplayV1 = {
  dominant_bin?: string | null;
  bin_weights?: Record<string, number> | null;
  entropy?: number | null;
  spread?: number | null;
};

export type ThemeFourbinDisplayBlockV1 = {
  schema?: string;
  frame_a?: ThemeFourbinFrameDisplayV1;
  frame_b?: ThemeFourbinFrameDisplayV1;
  explain_ab_differ_ko?: string[];
  walls?: string[];
  /** live_score when computed on-answer from query/body; fixture when precomputed. */
  source?: "fixture" | "live_score";
};

export type ThemeFourbinVerseRowV1 = {
  id: string;
  lang?: string;
  label_ko?: string;
  text_preview?: string;
  theme_fourbin_display?: ThemeFourbinDisplayBlockV1;
};

export type ThemeFourbinAskDisplayDocV1 = {
  schema: string;
  layout_slot: string;
  sibling_of: string;
  address_book_merge: boolean;
  research_only: boolean;
  send_gate: string;
  verses: ThemeFourbinVerseRowV1[];
  /** Lexicon bins for on-answer live scoring (no gematria). */
  frames?: ThemeFourbinFramesLexV1;
};

export const FRAME_A_BIN_LABEL_KO: Record<string, string> = {
  creation: "창조",
  fall: "타락",
  redemption: "구속",
  consummation: "완성",
};

export const FRAME_B_BIN_LABEL_KO: Record<string, string> = {
  promise: "약속",
  law: "법",
  sacrifice: "희생",
  kingdom: "왕국",
};

export function isLogosAskThemeFourbinDisplayV1Enabled(): boolean {
  const raw = (process.env.NEXT_PUBLIC_LOGOS_ASK_THEME_FOURBIN_V1 ?? "1")
    .trim()
    .toLowerCase();
  return raw !== "0" && raw !== "false" && raw !== "off";
}

export function binLabelKo(frame: "a" | "b", bin: string): string {
  const map = frame === "a" ? FRAME_A_BIN_LABEL_KO : FRAME_B_BIN_LABEL_KO;
  return map[bin] ?? bin;
}

function preferKoId(blob: string, enId: string, koId: string): string {
  const hasKoBook = /창세기|시편|태초에|목자|푸른/.test(blob);
  const hasEnBook =
    /genesis|gen\s*1|psalm|ps\.?\s*23|in the beginning|shepherd|green pastures/.test(
      blob,
    );
  if (hasKoBook && !hasEnBook) return koId;
  return enId;
}

/** Heuristic match from Ask verse_refs / query → fixture verse id. */
export function matchThemeFourbinVerseId(
  verseRefs: string[],
  query = "",
): string | null {
  const blob = `${verseRefs.join(" ")} ${query}`.toLowerCase();
  if (
    /gen(?:esis)?\s*1\s*[:：.]?\s*1|창세기\s*1\s*[:：.]?\s*1|태초에|in the beginning/.test(
      blob,
    )
  ) {
    return preferKoId(blob, "gen_1_1_en", "gen_1_1_ko");
  }
  if (
    /ps(?:alm)?\.?\s*23|시편\s*23|shepherd|목자|green pastures|푸른\s*초장/.test(blob)
  ) {
    return preferKoId(blob, "ps_23_1_2_en", "ps_23_1_2_ko");
  }
  return null;
}

export function pickThemeFourbinVerse(
  doc: ThemeFourbinAskDisplayDocV1 | null,
  verseRefs: string[],
  query = "",
): ThemeFourbinVerseRowV1 | null {
  if (!doc?.verses?.length) return null;
  const want = matchThemeFourbinVerseId(verseRefs, query);
  if (!want) return null;
  const exact = doc.verses.find((v) => v.id === want);
  if (exact) return exact;
  const prefix = want.replace(/_(en|ko)$/, "");
  return doc.verses.find((v) => v.id.startsWith(prefix)) ?? null;
}

/**
 * Fixture match first; else live-score query + answer text from embedded frames.
 * Always-on mainline path — every answer can show bins without gematria merge.
 */
export function resolveThemeFourbinDisplayVerse(
  doc: ThemeFourbinAskDisplayDocV1 | null,
  verseRefs: string[],
  query = "",
  answerText = "",
): ThemeFourbinVerseRowV1 | null {
  const fixture = pickThemeFourbinVerse(doc, verseRefs, query);
  if (fixture?.theme_fourbin_display) {
    return {
      ...fixture,
      theme_fourbin_display: {
        ...fixture.theme_fourbin_display,
        source: fixture.theme_fourbin_display.source ?? "fixture",
      },
    };
  }
  const blob = [query, answerText].filter((s) => s.trim()).join("\n").trim();
  if (!blob || !doc?.frames) return null;
  const live = scoreThemeFourbinDisplayLive(blob, doc.frames);
  if (!live?.frame_a && !live?.frame_b) return null;
  return {
    id: "live_on_answer",
    lang: /[\uac00-\ud7a3]/.test(blob) ? "ko" : "en",
    label_ko: "이번 답 · 라이브 테마",
    text_preview: blob.slice(0, 120),
    theme_fourbin_display: {
      schema: "logos_theme_fourbin_ask_display_v1",
      frame_a: live.frame_a,
      frame_b: live.frame_b,
      explain_ab_differ_ko: live.explain_ab_differ_ko,
      source: "live_score",
    },
  };
}

/** Key-level wall — do not substring-match wall strings like no_gematria_vector_fields. */
export function assertNoGematriaLeakInDisplay(
  block: ThemeFourbinDisplayBlockV1 | null | undefined,
): boolean {
  if (!block) return true;
  const walk = (obj: unknown): boolean => {
    if (!obj || typeof obj !== "object") return true;
    if (Array.isArray(obj)) return obj.every(walk);
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      if (FORBIDDEN_FIELD_KEYS.has(k)) return false;
      if (!walk(v)) return false;
    }
    return true;
  };
  return walk(block);
}

export function sortedBinEntries(
  weights: Record<string, number> | null | undefined,
): Array<{ bin: string; weight: number }> {
  if (!weights) return [];
  return Object.entries(weights)
    .map(([bin, weight]) => ({ bin, weight: Number(weight) || 0 }))
    .sort((a, b) => b.weight - a.weight);
}
