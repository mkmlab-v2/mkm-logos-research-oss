/** Golden-200 hub query matching — registry SSOT (sync bundle from public mirror). */
import embeddedRegistry from "../../public/data/logos_studio/golden_200_anchor_registry_v1.json";

export type BookChapterRuleV1 = {
  book: string;
  expected_chapters?: number[];
  blocked_chapters?: number[];
};

export type Golden200HubEntryV1 = {
  hub_id: string;
  priority_band: "P0" | "P1" | "P2";
  query_markers_ko: string[];
  expected_books?: string[];
  blocked_stub_books?: string[];
  blocked_query_markers_ko?: string[];
  requires_gospel_context?: boolean;
  book_chapter_rules?: BookChapterRuleV1[];
  primary_verse_refs: string[];
  preset_override_ids?: string[];
  blocked_preset_ids?: string[];
  reading_pack_artifact?: string;
  hub_spoke_contract: {
    max_verse_refs: number;
    min_distinct_books: number;
    forced_fit_forbidden: true;
    research_only: true;
    non_gating: true;
    send_gate: "HOLD";
  };
  traffic_rank?: number;
  failure_log_hits?: number;
};

export type Golden200AnchorRegistryV1 = {
  schema: "logos_golden_200_anchor_registry_v1";
  version: string;
  max_slots: 200;
  scope_ko: string;
  priority_bands: Record<string, string>;
  entries: Golden200HubEntryV1[];
};

const REV_CHAPTER_FROM_QUERY_RE = /(?:계시록|요한계시록|rev\.?)\s*(\d{1,2})/i;
const GEN_CHAPTER_FROM_QUERY_RE = /(?:창세기|genesis|gen\.?)\s*(\d{1,2})/i;
const BOOK_CHAPTER_FROM_QUERY_RES: Record<string, RegExp> = {
  Rev: REV_CHAPTER_FROM_QUERY_RE,
  Gen: GEN_CHAPTER_FROM_QUERY_RE,
  Isa: /(?:이사야|isaiah|isa\.?)\s*(\d{1,2})/i,
  Rom: /(?:로마서|romans|rom\.?)\s*(\d{1,2})/i,
  Matt: /(?:마태(?:복음)?|matt(?:hew)?\.?)\s*(\d{1,2})/i,
  Exod: /(?:출애굽(?:기)?|exodus|exod\.?)\s*(\d{1,2})/i,
  Jonah: /(?:요나(?:서)?|jonah\.?)\s*(\d{1,2})/i,
  Heb: /(?:히브리서|hebrews|heb\.?)\s*(\d{1,2})/i,
  Eph: /(?:에베소서|ephesians|eph\.?)\s*(\d{1,2})/i,
  Prov: /(?:잠언|proverbs|prov\.?)\s*(\d{1,2})/i,
  Acts: /(?:사도행전|acts\.?)\s*(\d{1,2})/i,
  Luke: /(?:누가(?:복음)?|luke\.?)\s*(\d{1,2})/i,
  "1Cor": /(?:고린도전서|1\s*cor(?:inthians)?|1cor\.?)\s*(\d{1,2})/i,
  Gal: /(?:갈라디아서|galatians|gal\.?)\s*(\d{1,2})/i,
  Phil: /(?:빌립보서|philippians|phil\.?)\s*(\d{1,2})/i,
  James: /(?:야고보서|james\.?)\s*(\d{1,2})/i,
  "1Pet": /(?:베드로전서|1\s*pet(?:er)?|1pet\.?)\s*(\d{1,2})/i,
  Ruth: /(?:룻기|ruth\.?)\s*(\d{1,2})/i,
  "1Sam": /(?:사무엘상|1\s*sam(?:uel)?|1sam\.?)\s*(\d{1,2})/i,
  "1Kgs": /(?:열왕기|1\s*kgs?|1\s*kings\.?)\s*(\d{1,2})/i,
  Mic: /(?:미가|micah|mic\.?)\s*(\d{1,2})/i,
};
const GOSPEL_CONTEXT_RE =
  /(예수|그리스도|십자가|수난|passion|마태|마가|요한|matt\.?\s*27|mark\.?\s*15|john\.?\s*19)/i;

const MATCH_MIN_SCORE = 2;

function norm(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

export function parseRevelationChapterFromQuery(query: string): number | null {
  const m = REV_CHAPTER_FROM_QUERY_RE.exec(query.trim());
  return m ? Number(m[1]) : null;
}

export function parseGenesisChapterFromQuery(query: string): number | null {
  const m = GEN_CHAPTER_FROM_QUERY_RE.exec(query.trim());
  return m ? Number(m[1]) : null;
}

function parseBookChapterFromQuery(book: string, query: string): number | null {
  const pattern = BOOK_CHAPTER_FROM_QUERY_RES[book];
  if (!pattern) return null;
  const m = pattern.exec(query.trim());
  return m ? Number(m[1]) : null;
}

export function getSyncGolden200Registry(): Golden200AnchorRegistryV1 {
  return embeddedRegistry as Golden200AnchorRegistryV1;
}

export function scoreGoldenHubEntry(entry: Golden200HubEntryV1, query: string): number {
  const q = norm(query);
  if (!q) return 0;

  for (const blocked of entry.blocked_query_markers_ko ?? []) {
    const b = norm(blocked);
    if (b.length >= 2 && q.includes(b)) return 0;
  }

  let score = 0;
  for (const marker of entry.query_markers_ko) {
    const m = norm(marker);
    if (m.length >= 2 && q.includes(m)) score += 2;
  }

  if (entry.hub_id === "gen2_eve_creation") {
    if ((q.includes("아담") && (q.includes("뼈") || q.includes("측"))) || q.includes("하와")) {
      score += 1;
    }
  }

  if (entry.hub_id === "john19_blood_water") {
    if ((q.includes("물") && q.includes("피")) || q.includes("옆구리")) {
      score += 2;
    }
  }

  if (entry.requires_gospel_context && !GOSPEL_CONTEXT_RE.test(query)) {
    score = Math.max(0, score - 1);
  }

  for (const rule of entry.book_chapter_rules ?? []) {
    const ch = parseBookChapterFromQuery(rule.book, query);
    if (ch === null) continue;
    if (rule.blocked_chapters?.includes(ch)) return 0;
    if (rule.expected_chapters?.includes(ch)) score += 2;
    else if (rule.expected_chapters?.length) score = 0;
  }

  return score;
}

export function matchGoldenHubQuery(
  query: string,
  registry: Golden200AnchorRegistryV1 = getSyncGolden200Registry(),
): Golden200HubEntryV1 | null {
  let best: Golden200HubEntryV1 | null = null;
  let bestScore = 0;

  for (const entry of registry.entries) {
    const score = scoreGoldenHubEntry(entry, query);
    if (score > bestScore) {
      bestScore = score;
      best = entry;
    }
  }

  return bestScore >= MATCH_MIN_SCORE ? best : null;
}

export function matchGoldenHubTopic(
  query: string,
  hubId: string,
  registry: Golden200AnchorRegistryV1 = getSyncGolden200Registry(),
): boolean {
  const hub = matchGoldenHubQuery(query, registry);
  return hub?.hub_id === hubId;
}

export function hubPrimaryVerseRefs(
  hubId: string,
  registry: Golden200AnchorRegistryV1 = getSyncGolden200Registry(),
): readonly string[] {
  const entry = registry.entries.find((e) => e.hub_id === hubId);
  return entry?.primary_verse_refs ?? [];
}
