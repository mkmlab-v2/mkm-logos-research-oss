/**
 * PersonaDiary Logos sidebar — opt-in reference layer [HYPO] · [NON_GATING].
 * SSOT artifact: docs/final/artifacts/personadiary_logos_sidebar_smoke_v1_latest.json
 * Public mirror: /data/personadiary_logos_sidebar_smoke_v1_latest.json
 */
import type { PersonadiaryMobileOpsV1 } from "./personadiaryMobileOpsV1";

export const PERSONADIARY_LOGOS_SIDEBAR_SCHEMA = "personadiary_logos_sidebar_smoke_v1" as const;
export const PERSONADIARY_LOGOS_SIDEBAR_URL =
  "/data/personadiary_logos_sidebar_smoke_v1_latest.json";
export const PERSONADIARY_LOGOS_SIDEBAR_MAX_HITS = 3;

export type PersonadiaryLogosSidebarHitType =
  | "logos_ann_lite"
  | "graphrag_motif"
  | "concept_bridge";

export type PersonadiaryLogosSidebarHitV1 = {
  rank: number;
  hit_type: PersonadiaryLogosSidebarHitType;
  source_rail: string;
  verse_id?: string;
  node_id?: string;
  assigned_symbol?: string;
  concept_id?: string;
  label_ko?: string;
  score?: number;
  summary?: string;
  match_reason?: string;
};

export type PersonadiaryLogosSidebarAnnLitePoolItem = {
  hit_type: "logos_ann_lite";
  source_rail: string;
  verse_id: string;
  ann_score?: number | null;
  summary?: string;
  detail?: string;
};

export type PersonadiaryLogosSidebarMotifPoolItem = {
  hit_type: "graphrag_motif";
  source_rail: string;
  node_id?: string;
  assigned_symbol?: string;
  path_score?: number;
  summary?: string;
};

export type PersonadiaryLogosSidebarBridgePoolItem = {
  hit_type: "concept_bridge";
  source_rail: string;
  concept_id?: string;
  label_ko?: string;
  summary?: string;
};

export type PersonadiaryLogosSidebarCandidatePoolsV1 = {
  logos_ann_lite: PersonadiaryLogosSidebarAnnLitePoolItem[];
  graphrag_motif: PersonadiaryLogosSidebarMotifPoolItem[];
  concept_bridge: PersonadiaryLogosSidebarBridgePoolItem[];
};

export type PersonadiaryLogosSidebarSmokeV1 = {
  schema: typeof PERSONADIARY_LOGOS_SIDEBAR_SCHEMA;
  version: string;
  lane_id: "personadiary_logos_sidebar";
  research_only: true;
  hypothesis_tag: "[HYPO]";
  send_gate: "HOLD";
  track_a_blocked: true;
  prophecy_vote: "none";
  sidebar_generation_ok: boolean;
  hits: PersonadiaryLogosSidebarHitV1[];
  candidate_pools?: PersonadiaryLogosSidebarCandidatePoolsV1;
  rerank_contract?: {
    client_local_diary?: boolean;
    max_hits?: number;
    prophecy_vote?: string;
  };
  forbidden_violations: string[];
  ok: boolean;
  consumer_contract_ko?: string;
};

export type PersonadiaryLogosSidebarResolvedV1 = {
  hits: PersonadiaryLogosSidebarHitV1[];
  diary_text_chars: number;
  diary_text_source: "ops_local" | "artifact_default";
  reranked: boolean;
};

const FORBIDDEN_HEADLINE = ["적중률", "매수 사인", "운세 확정", "directional_hit_rate", "sharpe"];
const TOKEN_RE = /[가-힣]{2,}|[a-zA-Z]{3,}/g;

function tokenize(text: string): Set<string> {
  const out = new Set<string>();
  for (const match of text.matchAll(TOKEN_RE)) {
    out.add(match[0].toLowerCase());
  }
  return out;
}

function hitKey(hit: Pick<PersonadiaryLogosSidebarHitV1, "verse_id" | "node_id" | "concept_id">): string {
  return hit.verse_id || hit.node_id || hit.concept_id || "";
}

export function collectDiaryTextFromOps(ops: PersonadiaryMobileOpsV1): string {
  const parts: string[] = [];
  const lanes = ops.north_star_by_lane_hypo_v1?.lanes;
  if (lanes) {
    for (const lane of Object.values(lanes)) {
      const line = lane.one_line.trim();
      if (line) parts.push(line);
    }
  }
  for (const item of ops.weekly_top5) {
    const text = item.text.trim();
    if (text) parts.push(text);
  }
  const next = ops.next_one_action.text.trim();
  if (next) parts.push(next);
  for (const entry of ops.diary_entries_local) {
    const body = entry.body.trim();
    if (body) parts.push(body);
  }
  return parts.join("\n");
}

function rankAnnLiteHits(
  pool: PersonadiaryLogosSidebarAnnLitePoolItem[],
  diaryTokens: Set<string>
): PersonadiaryLogosSidebarHitV1[] {
  const scored: Array<{ score: number; hit: PersonadiaryLogosSidebarHitV1 }> = [];
  const seen = new Set<string>();
  for (const item of pool) {
    if (!item.verse_id || seen.has(item.verse_id)) continue;
    const blockTokens = tokenize(`${item.summary || ""} ${item.detail || ""}`);
    let overlap = 0;
    for (const tok of diaryTokens) {
      if (blockTokens.has(tok)) overlap += 1;
    }
    const base = typeof item.ann_score === "number" ? item.ann_score : 0;
    const score = base + overlap * 0.05;
    scored.push({
      score,
      hit: {
        rank: 0,
        hit_type: "logos_ann_lite",
        source_rail: item.source_rail,
        verse_id: item.verse_id,
        score: Number(score.toFixed(6)),
        summary: item.summary,
        match_reason: `ann_lite_score+token_overlap=${overlap}`,
      },
    });
    seen.add(item.verse_id);
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.map((row) => row.hit);
}

function rankMotifHits(pool: PersonadiaryLogosSidebarMotifPoolItem[]): PersonadiaryLogosSidebarHitV1[] {
  const out: PersonadiaryLogosSidebarHitV1[] = [];
  const seenSymbol = new Set<string>();
  for (const item of pool) {
    const sym = item.assigned_symbol || "";
    if (sym && seenSymbol.has(sym)) continue;
    if (sym) seenSymbol.add(sym);
    const pathScore = typeof item.path_score === "number" ? item.path_score : 0;
    out.push({
      rank: 0,
      hit_type: "graphrag_motif",
      source_rail: item.source_rail,
      node_id: item.node_id,
      assigned_symbol: item.assigned_symbol,
      score: Number(pathScore.toFixed(6)),
      summary: item.summary,
      match_reason: "graphrag_selected_node_rank",
    });
  }
  return out;
}

function rankConceptBridgeHits(
  pool: PersonadiaryLogosSidebarBridgePoolItem[],
  diaryText: string
): PersonadiaryLogosSidebarHitV1[] {
  const diaryTokens = tokenize(diaryText);
  const scored: Array<{ score: number; hit: PersonadiaryLogosSidebarHitV1 }> = [];
  for (const item of pool) {
    const label = item.label_ko || "";
    const conceptId = item.concept_id || "";
    const hay = `${label} ${conceptId}`.toLowerCase();
    let overlap = 0;
    for (const tok of diaryTokens) {
      if (hay.includes(tok)) overlap += 1;
    }
    if (diaryText.includes("쉼") && conceptId.includes("turmoil")) overlap += 2;
    if (diaryText.includes("마음") && (conceptId.includes("mercy") || conceptId.includes("compassion"))) {
      overlap += 1;
    }
    if (overlap <= 0) continue;
    scored.push({
      score: overlap,
      hit: {
        rank: 0,
        hit_type: "concept_bridge",
        source_rail: item.source_rail,
        concept_id: conceptId,
        label_ko: label,
        score: overlap,
        summary: item.summary,
        match_reason: `diary_token_overlap=${overlap}`,
      },
    });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.map((row) => row.hit);
}

function assembleHits(
  annHits: PersonadiaryLogosSidebarHitV1[],
  motifHits: PersonadiaryLogosSidebarHitV1[],
  bridgeHits: PersonadiaryLogosSidebarHitV1[]
): PersonadiaryLogosSidebarHitV1[] {
  const combined: PersonadiaryLogosSidebarHitV1[] = [];
  const bridgeTop = bridgeHits[0];
  if (annHits[0]) combined.push({ ...annHits[0] });
  if (motifHits[0]) combined.push({ ...motifHits[0] });
  if (bridgeTop) combined.push({ ...bridgeTop });

  for (const hit of [...annHits.slice(1), ...motifHits.slice(1), ...bridgeHits.slice(1)]) {
    if (combined.length >= PERSONADIARY_LOGOS_SIDEBAR_MAX_HITS) break;
    const key = hitKey(hit);
    if (!key || combined.some((h) => hitKey(h) === key)) continue;
    combined.push({ ...hit });
  }

  while (combined.length < PERSONADIARY_LOGOS_SIDEBAR_MAX_HITS) {
    const pool = [...annHits, ...motifHits, ...bridgeHits];
    let added = false;
    for (const hit of pool) {
      if (combined.length >= PERSONADIARY_LOGOS_SIDEBAR_MAX_HITS) break;
      const key = hitKey(hit);
      if (!key || combined.some((h) => hitKey(h) === key)) continue;
      combined.push({ ...hit });
      added = true;
    }
    if (!added) break;
  }

  return combined.slice(0, PERSONADIARY_LOGOS_SIDEBAR_MAX_HITS).map((hit, index) => ({
    ...hit,
    rank: index + 1,
  }));
}

export function rankLogosSidebarHitsFromPools(
  diaryText: string,
  pools: PersonadiaryLogosSidebarCandidatePoolsV1
): PersonadiaryLogosSidebarHitV1[] {
  const diaryTokens = tokenize(diaryText);
  const annHits = rankAnnLiteHits(pools.logos_ann_lite || [], diaryTokens);
  const motifHits = rankMotifHits(pools.graphrag_motif || []);
  const bridgeHits = rankConceptBridgeHits(pools.concept_bridge || [], diaryText);
  return assembleHits(annHits, motifHits, bridgeHits);
}

export function resolvePersonadiaryLogosSidebar(
  base: PersonadiaryLogosSidebarSmokeV1,
  ops?: PersonadiaryMobileOpsV1 | null
): PersonadiaryLogosSidebarResolvedV1 {
  const diaryText = ops ? collectDiaryTextFromOps(ops) : "";
  const pools = base.candidate_pools;
  if (diaryText.trim() && pools) {
    const hits = rankLogosSidebarHitsFromPools(diaryText, pools);
    if (hits.length === PERSONADIARY_LOGOS_SIDEBAR_MAX_HITS) {
      return {
        hits,
        diary_text_chars: diaryText.length,
        diary_text_source: "ops_local",
        reranked: true,
      };
    }
  }
  return {
    hits: base.hits,
    diary_text_chars: diaryText.length,
    diary_text_source: "artifact_default",
    reranked: false,
  };
}

export function isPersonadiaryLogosSidebarSmokeV1(raw: unknown): raw is PersonadiaryLogosSidebarSmokeV1 {
  if (!raw || typeof raw !== "object") return false;
  const doc = raw as PersonadiaryLogosSidebarSmokeV1;
  return (
    doc.schema === PERSONADIARY_LOGOS_SIDEBAR_SCHEMA &&
    doc.research_only === true &&
    doc.send_gate === "HOLD" &&
    doc.prophecy_vote === "none" &&
    doc.track_a_blocked === true &&
    Array.isArray(doc.hits) &&
    Array.isArray(doc.forbidden_violations)
  );
}

export function validatePersonadiaryLogosSidebarWalls(doc: PersonadiaryLogosSidebarSmokeV1): string | null {
  if (!doc.sidebar_generation_ok || !doc.ok) return "sidebar_generation_ok=false";
  if (doc.forbidden_violations.length > 0) return "forbidden_violations";
  if (doc.hits.length !== PERSONADIARY_LOGOS_SIDEBAR_MAX_HITS) return "hits!=3";
  const blob = JSON.stringify(doc);
  for (const token of FORBIDDEN_HEADLINE) {
    if (blob.includes(token)) return `forbidden_token:${token}`;
  }
  return null;
}

export function formatLogosSidebarHitTitle(hit: PersonadiaryLogosSidebarHitV1): string {
  if (hit.hit_type === "logos_ann_lite" && hit.verse_id) return hit.verse_id;
  if (hit.hit_type === "graphrag_motif" && hit.assigned_symbol) {
    return hit.assigned_symbol.replace(/_/g, " ");
  }
  if (hit.hit_type === "concept_bridge" && hit.label_ko) return hit.label_ko;
  return hit.summary?.slice(0, 80) || `참조 ${hit.rank}`;
}

export function formatLogosSidebarHitDetail(hit: PersonadiaryLogosSidebarHitV1): string {
  if (hit.hit_type === "graphrag_motif" && hit.node_id) {
    return `모티프 · ${hit.node_id}`;
  }
  if (hit.hit_type === "concept_bridge" && hit.concept_id) {
    return hit.concept_id;
  }
  return hit.summary || hit.match_reason || "";
}

export async function fetchPersonadiaryLogosSidebarSmoke(): Promise<PersonadiaryLogosSidebarSmokeV1> {
  const res = await fetch(PERSONADIARY_LOGOS_SIDEBAR_URL, { cache: "no-store" });
  if (!res.ok) throw new Error(`logos_sidebar_fetch_${res.status}`);
  const doc: unknown = await res.json();
  if (!isPersonadiaryLogosSidebarSmokeV1(doc)) {
    throw new Error("logos_sidebar_schema");
  }
  const wallErr = validatePersonadiaryLogosSidebarWalls(doc);
  if (wallErr) throw new Error(`logos_sidebar_walls:${wallErr}`);
  return doc;
}

export async function fetchPersonadiaryLogosSidebarForOps(
  ops: PersonadiaryMobileOpsV1
): Promise<PersonadiaryLogosSidebarResolvedV1> {
  const base = await fetchPersonadiaryLogosSidebarSmoke();
  return resolvePersonadiaryLogosSidebar(base, ops);
}
