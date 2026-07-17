/**
 * School panel topic lock + thin intent_compress (Ask S3).
 * research_only · [HYPO][NON_GATING] · NOT Track A compression KPI / FAIL-COMP-004.
 *
 * Done card: school_panel_topic_lock — dynamic_topical_freeform schools must stay
 * on query topic (image/idol/beast/tech ethics [HYPO]), not gospel-redaction /
 * Isa.40.11 wilderness / Luke.1.1 bleed packs.
 */

import {
  AI_SOCIETY_SYMBOLISM_PRIMARY_REFS,
  FREEFORM_TOPICAL_PRESET_ID,
  isTopicalFreeformInquiry,
} from "./logosFreeformTopicalInquiryV1";

export const SCHOOL_PANEL_TOPIC_LOCK_SCHEMA = "logos_school_panel_topic_lock_v1";

/** Bleed packs that must not appear on AI/형상/Rev13-class topical freeform. */
export const FORBID_PACK_MARKERS = [
  "gospel_redaction",
  "isa40_wilderness",
  "luke1_infancy",
  "gen27_narrative_center",
] as const;

const BLEED_REF_RES = [
  /\bIsa\.40\.11\b/i,
  /\bIsa\.40\b/i,
  /\bLuke\.1\.1\b/i,
  /\bLuke\.1\.28\b/i,
  /\bGen\.27\.\d+\b/i,
];

const BLEED_TEXT_RES = [
  /복음서의\s*편집\s*의도/,
  /공관복음\s*전승/,
  /정경\s*편집/,
  /광야에서\s*·\s*외치는/,
  /「광야에서」/,
  /대림-사순-부활/,
  /마가\s*우선설/,
];

const QUERY_ALLOWS_ISA40_RE = /이사야\s*40|Isa\.?\s*40|광야에서\s*외치|위로하라\s*내\s*백성/i;
const QUERY_ALLOWS_LUKE1_RE =
  /누가복음\s*1|Luke\.?\s*1|성모|마리아|중보|누가\s*서문|Theophilus|데오빌로/i;
const QUERY_ALLOWS_GOSPEL_EDIT_RE = /복음\s*편집|공관복음|정경\s*편집|redaction|synoptic/i;

export type IntentCompressV1 = {
  schema: "logos_intent_compress_v1";
  intent_core: string;
  forbid_packs: string[];
  prefer_refs: string[];
  topic_id: "ai_society_symbolism" | "generic";
  /** Enrich for school prompt / routing only — never Track A KPI. */
  compress_role: "school_routing_enrich_only";
};

export function compressIntentForSchoolRouting(query: string): IntentCompressV1 {
  const q = (query || "").trim();
  if (isTopicalFreeformInquiry(q)) {
    return {
      schema: "logos_intent_compress_v1",
      intent_core:
        "AI를 성경의 형상·우상·짐승 생기(Rev13) 상징으로 읽고, 사회 변화를 advisory로만 서술 [HYPO][NON_GATING].",
      forbid_packs: [...FORBID_PACK_MARKERS],
      prefer_refs: [...AI_SOCIETY_SYMBOLISM_PRIMARY_REFS],
      topic_id: "ai_society_symbolism",
      compress_role: "school_routing_enrich_only",
    };
  }
  return {
    schema: "logos_intent_compress_v1",
    intent_core: q.slice(0, 160) || "(empty)",
    forbid_packs: [],
    prefer_refs: [],
    topic_id: "generic",
    compress_role: "school_routing_enrich_only",
  };
}

function schoolBlob(group: Record<string, unknown>): string {
  const parts: string[] = [
    String(group.conflict_group_id ?? ""),
    String(group.lexicon_base ?? ""),
  ];
  const schools = (group.schools as Array<Record<string, unknown>> | undefined) ?? [];
  for (const school of schools) {
    parts.push(String(school.interpretation_ko ?? ""));
    parts.push(String(school.school_tier ?? ""));
    for (const ref of (school.verse_refs as unknown[] | undefined) ?? []) {
      parts.push(String(ref));
    }
    for (const ref of (school.citation_lock_anchors as unknown[] | undefined) ?? []) {
      parts.push(String(ref));
    }
  }
  return parts.join("\n");
}

function queryAllowsBleed(query: string, marker: string): boolean {
  if (marker === "isa40_wilderness") return QUERY_ALLOWS_ISA40_RE.test(query);
  if (marker === "luke1_infancy") return QUERY_ALLOWS_LUKE1_RE.test(query);
  if (marker === "gospel_redaction") return QUERY_ALLOWS_GOSPEL_EDIT_RE.test(query);
  if (marker === "gen27_narrative_center") return /창세기\s*27|Gen\.?\s*27|야곱.*에서/i.test(query);
  return false;
}

export function detectSchoolBleedMarkers(
  group: Record<string, unknown>,
  query: string,
): string[] {
  const blob = schoolBlob(group);
  const hits: string[] = [];
  if (
    !queryAllowsBleed(query, "gospel_redaction") &&
    (BLEED_TEXT_RES.some((re) => re.test(blob)) || /MKM_CONCEPT_LOGOS_GOSPELS/i.test(blob))
  ) {
    hits.push("gospel_redaction");
  }
  if (
    !queryAllowsBleed(query, "isa40_wilderness") &&
    (/\bIsa\.40(?:\.11)?\b/i.test(blob) || /광야에서/.test(blob) || /MKM_CONCEPT_MKM_LOGOS_8/i.test(blob))
  ) {
    hits.push("isa40_wilderness");
  }
  if (
    !queryAllowsBleed(query, "luke1_infancy") &&
    (/\bLuke\.1\.(?:1|28)\b/i.test(blob) || /MKM_CONCEPT_LUKE_LUKE/i.test(blob))
  ) {
    hits.push("luke1_infancy");
  }
  if (!queryAllowsBleed(query, "gen27_narrative_center") && /\bGen\.27\.\d+\b/i.test(blob)) {
    hits.push("gen27_narrative_center");
  }
  return hits;
}

function preferRefHit(blob: string, preferRefs: string[]): boolean {
  if (!preferRefs.length) return true;
  const norm = blob.replace(/\s/g, "");
  return preferRefs.some((ref) => {
    const r = ref.replace(/\s/g, "");
    if (norm.includes(r)) return true;
    // book-level soft: Gen.1 / Exod.20 / Rev.13
    const bookChap = r.replace(/\.\d+$/, "");
    return bookChap.length >= 4 && norm.toLowerCase().includes(bookChap.toLowerCase());
  });
}

/**
 * Drop wrong-pack conflict groups; keep groups that intersect prefer_refs
 * (or have no prefer list). Empty result → caller may regenerate topical fallback.
 */
export function filterSchoolGroupsByTopicLock(
  groups: Array<Record<string, unknown>>,
  intent: IntentCompressV1,
  query: string,
): Array<Record<string, unknown>> {
  if (intent.topic_id === "generic" && !intent.forbid_packs.length) {
    return groups;
  }
  const out: Array<Record<string, unknown>> = [];
  for (const group of groups) {
    const bleed = detectSchoolBleedMarkers(group, query);
    if (bleed.length) continue;
    if (intent.topic_id === "ai_society_symbolism") {
      const blob = schoolBlob(group);
      if (!preferRefHit(blob, intent.prefer_refs)) continue;
    }
    out.push(group);
  }
  return out;
}

export function buildAiSocietySymbolismSchoolFallback(
  query: string,
  verseRefs: string[] = [...AI_SOCIETY_SYMBOLISM_PRIMARY_REFS],
): Array<Record<string, unknown>> {
  void query;
  const primary = (verseRefs.length ? verseRefs : [...AI_SOCIETY_SYMBOLISM_PRIMARY_REFS])
    .map((r) => String(r).trim())
    .filter(Boolean)
    .slice(0, 8);
  const imageRefs = primary.filter((r) => /^(Gen\.1|Exod\.20|1Cor\.8)/i.test(r));
  const beastRefs = primary.filter((r) => /^(Rev\.13|Dan\.2)/i.test(r));
  const wisdomRefs = primary.filter((r) => /^(Prov\.8|Eccl\.7)/i.test(r));
  const hist = imageRefs.length ? imageRefs.slice(0, 3) : ["Gen.1.26", "Exod.20.4"];
  const reform = [...(beastRefs.length ? beastRefs : ["Rev.13.15"]), ...(wisdomRefs.slice(0, 1) || ["Prov.8.22"])].slice(
    0,
    3,
  );
  const catholic = [...hist.slice(0, 2), ...(beastRefs[0] ? [beastRefs[0]] : ["Rev.13.15"])].slice(0, 3);

  return [
    {
      conflict_group_id: "ai_society_symbolism_public_topic_lock",
      lexicon_base: "형상 · 우상 · 짐승 생기 · 지혜 [HYPO]",
      school_count: 3,
      schools: [
        {
          school_tier: "Historical-grammatical",
          interpretation_ko:
            "본문에 ‘AI’는 부재합니다. Gen.1.26 형상(צֶלֶם)·Exod.20.4 우상 금지를 유형론으로만 병렬합니다. 현대 기술을 1:1 교리 해독하지 않습니다 [HYPO][NON_GATING].",
          verse_refs: hist,
          citation_lock_anchors: hist,
          traditions: ["historical-grammatical", "ANE image / idol"],
        },
        {
          school_tier: "Reformed",
          interpretation_ko:
            "개혁 전통의 우상 금지·지혜 문학(Prov.8) 프레임에서 AI를 도구·피조물 은유로 읽습니다. Rev.13.15 우상·생기 언어는 권력·숭배 경고 축으로만 병렬하며 적그리스도 단정은 금지합니다 [HYPO].",
          verse_refs: reform,
          citation_lock_anchors: reform,
          traditions: ["Reformed", "wisdom ethics"],
        },
        {
          school_tier: "Catholic",
          interpretation_ko:
            "형상·이콘·우상의 스펙트럼에서 AI 이미지를 ‘성상/도구/위험’으로 분기 관측합니다. Gen.1.26·Exod.20·Rev.13 앵커만 사용하며 질의와 무관한 classic pack 합선을 피합니다 [HYPO][NON_GATING].",
          verse_refs: catholic,
          citation_lock_anchors: catholic,
          traditions: ["Catholic", "icon / idol spectrum"],
        },
      ],
    },
  ];
}

export type SchoolPanelTopicOk = {
  ok: boolean;
  school_panel_topic_ok: boolean;
  bleed_markers: string[];
  school_row_count: number;
  prefer_ref_hits: number;
  intent: IntentCompressV1;
};

export function assertSchoolPanelTopicOk(
  groups: Array<Record<string, unknown>>,
  query: string,
  intent?: IntentCompressV1,
): SchoolPanelTopicOk {
  const ic = intent ?? compressIntentForSchoolRouting(query);
  const bleed: string[] = [];
  let rows = 0;
  let preferHits = 0;
  for (const group of groups) {
    bleed.push(...detectSchoolBleedMarkers(group, query));
    const schools = (group.schools as unknown[] | undefined) ?? [];
    rows += schools.length;
    if (preferRefHit(schoolBlob(group), ic.prefer_refs)) preferHits += 1;
  }
  const uniqueBleed = [...new Set(bleed)];
  // Topical AI: either topic-locked schools present, or honest empty (no bleed).
  let ok = uniqueBleed.length === 0;
  if (ic.topic_id === "ai_society_symbolism" && rows > 0) {
    ok = ok && preferHits > 0;
  }
  return {
    ok,
    school_panel_topic_ok: ok,
    bleed_markers: uniqueBleed,
    school_row_count: rows,
    prefer_ref_hits: preferHits,
    intent: ic,
  };
}

/** Apply lock after live conflict map; regenerate topical fallback when needed. */
export function resolveTopicLockedSchoolGroups(input: {
  query: string;
  verseRefs: string[];
  liveGroups: Array<Record<string, unknown>>;
  presetId?: string | null;
  queryMode?: string | null;
}): {
  groups: Array<Record<string, unknown>>;
  conflict_source: "live" | "fallback" | "none";
  intent: IntentCompressV1;
  topic_lock: SchoolPanelTopicOk;
} {
  const intent = compressIntentForSchoolRouting(input.query);
  const filtered = filterSchoolGroupsByTopicLock(input.liveGroups, intent, input.query);
  const mode = String(input.queryMode ?? "");
  const topical =
    intent.topic_id === "ai_society_symbolism" ||
    input.presetId === FREEFORM_TOPICAL_PRESET_ID ||
    mode.includes("inquiry_thematic_topical_freeform") ||
    isTopicalFreeformInquiry(input.query);

  if (filtered.length) {
    const topic_lock = assertSchoolPanelTopicOk(filtered, input.query, intent);
    return { groups: filtered, conflict_source: "live", intent, topic_lock };
  }

  if (topical) {
    const groups = buildAiSocietySymbolismSchoolFallback(input.query, input.verseRefs);
    const topic_lock = assertSchoolPanelTopicOk(groups, input.query, intent);
    return { groups, conflict_source: "fallback", intent, topic_lock };
  }

  return {
    groups: [],
    conflict_source: "none",
    intent,
    topic_lock: assertSchoolPanelTopicOk([], input.query, intent),
  };
}

/** True if blob looks like classic bleed (for smoke / regression). */
export function schoolPanelBlobHasClassicBleed(blob: string): boolean {
  return (
    BLEED_REF_RES.some((re) => re.test(blob)) || BLEED_TEXT_RES.some((re) => re.test(blob))
  );
}
