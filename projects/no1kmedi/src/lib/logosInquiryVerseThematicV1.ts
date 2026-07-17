/** Inquiry-only thematic layer for well-known verse topics (Track B [HYPO], NON_GATING). */
import type { LogosStudioPreset, StudioQueryPayload } from "./logosResearchStudioV1";
import {
  getSyncGolden200Registry,
  hubPrimaryVerseRefs,
  matchGoldenHubQuery,
  matchGoldenHubTopic,
  parseRevelationChapterFromQuery,
} from "./logosGolden200HubMatchV1";

const JOHN_19_BLOOD_WATER_RE =
  /(옆구리|창에?\s*찔|피와?\s*물|blood\s*and\s*water|side\s*pierc)/i;
const PASSION_CROWN_RE = /(가시\s*면류관|면류관|가시\s*관|crown\s*of\s*thorns)/i;
const GOSPEL_CONTEXT_RE = /(예수|그리스도|십자가|수난|passion|마태|마가|요한|matt\.?\s*27|mark\.?\s*15|john\.?\s*19)/i;

export { parseRevelationChapterFromQuery };

export const PASSION_CROWN_GOSPEL_REFS = ["Matt.27.29", "Mark.15.17", "John.19.2", "John.19.5"] as const;

export const ANTICHRIST_666_PRIMARY_REFS = hubPrimaryVerseRefs("antichrist_666") as readonly [
  string,
  ...string[],
];

export const REV21_NEW_CREATION_PRIMARY_REFS = hubPrimaryVerseRefs("rev21_new_creation") as readonly [
  string,
  ...string[],
];

function hasVerseRef(refs: string[], target: string): boolean {
  const norm = target.replace(/\s/g, "").toLowerCase();
  return refs.some((r) => r.replace(/\s/g, "").toLowerCase().includes(norm));
}

function mergePrimaryRefs(primary: string[], refs: string[], max = 24): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const p of primary) {
    const hit = refs.find((r) => r.replace(/\s/g, "").toLowerCase() === p.toLowerCase());
    const v = hit || p;
    const key = v.replace(/\s/g, "").toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      out.push(v);
    }
  }
  for (const r of refs) {
    const key = r.replace(/\s/g, "").toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      out.push(r);
    }
  }
  return out.slice(0, max);
}

export function detectRev21NewCreationTopic(query: string, verseRefs: string[] = []): boolean {
  if (matchGoldenHubTopic(query, "rev21_new_creation")) return true;
  const q = query.trim();
  if (!q) return false;
  const queryMentionsRev21 =
    /(?:계시록|요한계시록|rev\.?)\s*21|새\s*하늘과?\s*새\s*땅|새\s*하늘|새\s*땅/i.test(q);
  if (!queryMentionsRev21) return false;
  return REV21_NEW_CREATION_PRIMARY_REFS.some((ref) => hasVerseRef(verseRefs, ref));
}

export function detectAntichrist666Topic(query: string, verseRefs: string[] = []): boolean {
  if (matchGoldenHubTopic(query, "antichrist_666")) return true;
  const hasAnchor = ANTICHRIST_666_PRIMARY_REFS.some((ref) => hasVerseRef(verseRefs, ref));
  return hasAnchor && /(666|적그리스도|antichrist)/i.test(query);
}

export function detectPassionCrownTopic(query: string, verseRefs: string[] = []): boolean {
  if (matchGoldenHubTopic(query, "passion_crown")) return true;
  const q = query.trim();
  if (!q || !PASSION_CROWN_RE.test(q)) return false;
  if (!GOSPEL_CONTEXT_RE.test(q)) {
    return PASSION_CROWN_GOSPEL_REFS.some((ref) => hasVerseRef(verseRefs, ref));
  }
  return true;
}

export function resolveVerseAnchorPresetId(
  presets: LogosStudioPreset[],
  query: string,
): string | null {
  const q = query.trim();
  if (!q) return null;

  const hub = matchGoldenHubQuery(q, getSyncGolden200Registry());
  if (hub?.preset_override_ids?.length) {
    for (const id of hub.preset_override_ids) {
      if (presets.some((p) => p.id === id)) return id;
    }
  }

  if (detectJohn19BloodWaterTopic(q, [])) {
    return (
      presets.find((p) => p.id === "topic_1john_5_anchor")?.id ??
      presets.find((p) => p.id === "topic_john_1_anchor")?.id ??
      null
    );
  }
  return null;
}

export function detectJohn19BloodWaterTopic(query: string, verseRefs: string[]): boolean {
  if (matchGoldenHubTopic(query, "john19_blood_water")) return true;
  const q = query.trim();
  if (!q) return false;
  if (!JOHN_19_BLOOD_WATER_RE.test(q)) return false;
  if (!GOSPEL_CONTEXT_RE.test(q) && !hasVerseRef(verseRefs, "Jhn.19.34")) return false;
  return true;
}

export function buildRev21NewCreationThematicAnswerKo(query: string): string {
  return [
    `[HYPO] 질문: ${query.trim()}`,
    "Rev.21.1 · Rev.21.4 — **새 하늘과 새 땅**·**모든 눈물을 씻으실 것** 서사를 본문이 기록합니다. 단일 종말론·단일 상징 확정 없음 [NON_GATING].",
    "",
    "### 1. 창조·재창조 읽기",
    "이전 하늘과 땅이 지나가고 새 하늘·새 땅이 보인다는 장면은 창세 서사의 재창조 프레임과 병렬 비교하되, 1:1 예언 성취 단정은 하지 않음. 앵커: Rev.21.1 · Isa.65.17 · 2Pet.3.13",
    "",
    "### 2. 거처·성막 읽기",
    "하나님과 함께 거하심·성막/성전 이미지가 겹친다. 도시·신부·성전 상징은 학파별로 분화. 앵커: Rev.21.3 · Rev.21.22",
    "",
    "### 3. 위로·종말 희망 읽기",
    "죽음·슬픔·고통·우는 것이 없어진다는 선포는 위로·소망 층으로 읽히나, 역사·정치 1:1 대응 단정은 하지 않음. 앵커: Rev.21.4 · Rev.21.5",
    "",
    "학파 병렬·citation lock 보조 입력 — Track A·실매매·단일 해석 트리거 아님.",
  ].join("\n");
}

export function buildPassionCrownThematicAnswerKo(query: string): string {
  return [
    `[HYPO] 질문: ${query.trim()}`,
    "가시면류관 서사는 복음서 수난 기록(Matt.27.29 · Mark.15.17 · John.19.2)에서 **조롱·왕권 패러디·고난**의 교차점으로 읽힙니다. 단일 교리·단일 상징 확정 없음 [NON_GATING].",
    "",
    "### 1. 왕권 패러디·조롱 읽기",
    "군병이 자색 예복·가시 관을 씌우며 ‘유대인의 왕’을 조롱하는 장면. 정치적 풍자와 종교적 모독이 겹친다. 앵커: Matt.27.29 · Mark.15.17 · John.19.2",
    "",
    "### 2. 고난·대속 프레임",
    "이사야 53장의 고난 종·멸시받는 자 이미지와 병렬 비교하되, 1:1 예언 성취 단정은 하지 않음. 앵커: Isa.53.3 · Matt.27.29",
    "",
    "### 3. 왕·제사장 상징 읽기",
    "가시(저주·땅 저주)와 면류관(왕권)의 역설적 결합 — 승리의 왕관이 아닌 고난의 관. 앵커: Gen.3.18 · John.19.5",
    "",
    "학파 병렬·citation lock 보조 입력 — Track A·실매매·단일 해석 트리거 아님.",
  ].join("\n");
}

export function buildJohn19BloodWaterThematicAnswerKo(query: string): string {
  return [
    `[HYPO] 질문: ${query.trim()}`,
    "Jhn.19.34 — 병사의 창에 의해 **피와 물**이 흐른다는 서사를 본문이 기록합니다. 단일 상징·단일 교리 확정 없음 [NON_GATING].",
    "",
    "### 1. 성사·교회 전통 읽기",
    "피(속죄·언약)와 물(세례·정결)을 **교회 탄생·성만** 상징으로 연결하는 patristic·liturgical 프레임. 앵커: Jhn.19.34 · 1John.5.6 · Zech.13.1",
    "",
    "### 2. 문자·역사 읽기",
    "사건 기록·증언 층만 읽고, 의학·법정 맥락에서 체액 분리 서술로 본다. 상징 승격 최소. 앵커: Jhn.19.34",
    "",
    "### 3. 증언·언약 읽기",
    "1John 5의 물·피·성령 **증언** 프레임과 병렬 비교하되, 삼중 증언의 단일 결론 조립은 하지 않음. 앵커: 1John.5.6 · Lev.17.11 · Ezek.36.25",
    "",
    "학파 병렬·citation lock 보조 입력 — Track A·실매매·단일 해석 트리거 아님.",
  ].join("\n");
}

function prioritizeJohn19Refs(refs: string[]): string[] {
  const primary = ["Jhn.19.34", "1John.5.6", "Lev.17.11", "Ezek.36.25", "Zech.13.1"];
  const out: string[] = [];
  const seen = new Set<string>();
  for (const p of primary) {
    const hit = refs.find((r) => r.replace(/\s/g, "").toLowerCase() === p.toLowerCase());
    if (hit && !seen.has(hit)) {
      seen.add(hit);
      out.push(hit);
    }
  }
  for (const r of refs) {
    if (!seen.has(r)) {
      seen.add(r);
      out.push(r);
    }
  }
  return out.slice(0, 24);
}

export function applyInquiryVerseThematicLayer(
  payload: StudioQueryPayload,
  query: string,
): StudioQueryPayload {
  const verseRefs = payload.path?.verse_refs ?? [];
  const hub = matchGoldenHubQuery(query, getSyncGolden200Registry());

  if (hub?.hub_id === "rev21_new_creation" || detectRev21NewCreationTopic(query, verseRefs)) {
    const primary = [...REV21_NEW_CREATION_PRIMARY_REFS];
    const thematic = buildRev21NewCreationThematicAnswerKo(query);
    const orderedRefs = mergePrimaryRefs(primary, verseRefs);
    return {
      ...payload,
      answer: thematic,
      query_mode: `${payload.query_mode || "preset"}+inquiry_thematic_rev21`,
      path: {
        ...payload.path,
        verse_refs: orderedRefs.length ? orderedRefs : primary,
      },
      insight_card: {
        preset_id: payload.preset_id,
        slot: payload.insight_card?.slot ?? "inquiry_thematic_rev21",
        slot_label_ko: payload.insight_card?.slot_label_ko ?? "새 하늘·새 땅 앵커",
        one_liner_ko: "Rev.21 — 새 창조·위로 서사 citation lock 우선 [HYPO]",
        verse_anchors: orderedRefs.slice(0, 12),
        gap_ko: "GraphRAG 보조 — Rev 21 앵커 우선 · 666/Job stub 합선 금지.",
        governance: "[HYPO][NON_GATING] · send_gate: HOLD",
      },
    };
  }

  if (hub?.hub_id === "antichrist_666" || detectAntichrist666Topic(query, verseRefs)) {
    const orderedRefs = [...ANTICHRIST_666_PRIMARY_REFS];
    return {
      ...payload,
      path: {
        ...payload.path,
        verse_refs: orderedRefs,
      },
      insight_card: {
        preset_id: payload.preset_id,
        slot: payload.insight_card?.slot ?? "inquiry_thematic_antichrist",
        slot_label_ko: payload.insight_card?.slot_label_ko ?? "종말·적그리스도 앵커",
        one_liner_ko: "666·적그리스도 — 계시록·요한서신 citation lock 우선 [HYPO]",
        verse_anchors: orderedRefs.slice(0, 12),
        gap_ko: "GraphRAG 보조 — Rev/1John/2Thess 앵커 우선 · Job/Ps stub 합선 금지.",
        governance: "[HYPO][NON_GATING] · send_gate: HOLD",
      },
    };
  }

  if (hub?.hub_id === "passion_crown" || detectPassionCrownTopic(query, verseRefs)) {
    const orderedRefs = [...PASSION_CROWN_GOSPEL_REFS];
    return {
      ...payload,
      path: {
        ...payload.path,
        verse_refs: orderedRefs,
      },
      insight_card: {
        preset_id: payload.preset_id,
        slot: payload.insight_card?.slot ?? "inquiry_thematic_passion",
        slot_label_ko: payload.insight_card?.slot_label_ko ?? "수난 주제 앵커",
        one_liner_ko: "가시면류관 — 복음서 수난 앵커 우선 [HYPO]",
        verse_anchors: orderedRefs.slice(0, 12),
        gap_ko: "GraphRAG 보조 — Matt/Mark/John 수난 구절 citation lock 우선.",
        governance: "[HYPO][NON_GATING] · send_gate: HOLD",
      },
    };
  }

  const HUB_THEMATIC_HANDLED = new Set([
    "rev21_new_creation",
    "antichrist_666",
    "passion_crown",
    "john19_blood_water",
  ]);
  if (hub && !HUB_THEMATIC_HANDLED.has(hub.hub_id) && hub.primary_verse_refs?.length) {
    const primary = [...hub.primary_verse_refs];
    const orderedRefs = mergePrimaryRefs(primary, verseRefs);
    return {
      ...payload,
      query_mode: `${payload.query_mode || "preset"}+inquiry_golden_hub_${hub.hub_id}`,
      path: {
        ...payload.path,
        verse_refs: orderedRefs.length ? orderedRefs : primary,
      },
      insight_card: {
        preset_id: payload.preset_id,
        slot: payload.insight_card?.slot ?? `inquiry_golden_hub_${hub.hub_id}`,
        slot_label_ko: payload.insight_card?.slot_label_ko ?? `Golden-200 · ${hub.hub_id}`,
        one_liner_ko: `Golden-200 hub citation lock — ${hub.hub_id} [HYPO]`,
        verse_anchors: orderedRefs.slice(0, 12),
        gap_ko: "GraphRAG 보조 — hub primary_verse_refs 우선 · stub 합선 금지.",
        governance: "[HYPO][NON_GATING] · send_gate: HOLD",
      },
    };
  }

  if (!detectJohn19BloodWaterTopic(query, verseRefs)) return payload;

  const thematic = buildJohn19BloodWaterThematicAnswerKo(query);
  const lemmaTail = payload.answer?.includes("### 2. Lemma")
    ? payload.answer.slice(payload.answer.indexOf("### 2. Lemma")).trim()
    : "";

  const mergedAnswer = lemmaTail ? `${thematic}\n\n${lemmaTail}` : thematic;
  const orderedRefs = prioritizeJohn19Refs(verseRefs);

  return {
    ...payload,
    answer: mergedAnswer,
    query_mode: `${payload.query_mode || "preset"}+inquiry_thematic_john19`,
    path: {
      ...payload.path,
      verse_refs: orderedRefs.length ? orderedRefs : verseRefs,
    },
    insight_card: {
      preset_id: payload.preset_id,
      slot: payload.insight_card?.slot ?? "inquiry_thematic",
      slot_label_ko: payload.insight_card?.slot_label_ko ?? "주제 합성",
      one_liner_ko: "Jhn.19.34 피·물 — 학파 병렬 프레임 [HYPO] · 단일 상징 단정 없음",
      verse_anchors: orderedRefs.slice(0, 12),
      gap_ko: "베타: 큐레이션 그래프·lemma 보조 — 전량 TSK·단일 교리 주장 아님.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD",
    },
  };
}

/** Gematria freeform topic detect — stub for softmatch gate (research_only · NON_GATING). */
export const GEMATRIA_WRONG_PACK_PRESET_IDS: ReadonlySet<string> = new Set<string>();

export function detectGematriaMeaningFreeformTopic(query: string): boolean {
  const q = String(query || '').toLowerCase();
  return /gematria|게마트리아|수비학|666\s*의미/.test(q);
}
