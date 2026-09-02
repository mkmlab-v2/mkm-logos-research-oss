/**
 * Logos Ask confidence spine (research_only · send_gate HOLD).
 *
 * Confident → curated hub/thematic/citation-lock path.
 * Not confident → general/soft freeform + grade label only —
 * do NOT force wrong hubs, fake anchors, or scholar packs that pretend certainty.
 *
 * Deterministic signals only — NOT an LLM self-score / hallucination %.
 */
import {
  getSyncGolden200Registry,
  matchGoldenHubQuery,
  scoreGoldenHubEntry,
  type Golden200HubEntryV1,
} from "./logosGolden200HubMatchV1";
import {
  detectJobSufferingTopic,
  detectJohn316Topic,
  detectPsalm23Topic,
  detectPsalm51Topic,
  detectRom828Topic,
  detectSamsonJudgesTopic,
} from "./logosInquiryTopicDetectV1";
import { hasScriptureAnchor } from "./logosInquiryQueryEnrichV1";
import { isEveRibVsNephilimCollisionQuery } from "./logosFreeformSoftMatchGateV1";

export const LOGOS_ASK_CONFIDENCE_GATE_SCHEMA = "logos_ask_confidence_gate_v1" as const;

/** Product-facing route band — maps onto G0–G3 control intensity. */
export type LogosAskRouteBandV1 = "curated" | "soft" | "general";

export const LOGOS_ASK_ROUTE_BAND_LABEL_KO: Record<LogosAskRouteBandV1, string> = {
  curated: "근거 강함 · 본문 앵커 분석",
  soft: "참고용 · 신뢰도 보통",
  general: "일반 참고 · 신뢰도 낮음",
};

/** Gospel context alone is never enough for curated certainty. */
const BARE_GOSPEL_RE =
  /(예수|그리스도|십자가|수난|passion|복음|jesus|christ|cross)/i;

/** Explicit faith/doctrine words that justify soft faith freeform (not bare 십자가). */
const EXPLICIT_FAITH_DOCTRINE_RE =
  /(신앙|믿음|구원|기도|회개|은혜|칭의|의인|죄사함|성령|교회|faith|belief|believe|salvation|grace|prayer|gospel\s*of)/i;

/** Local marker mirrors (avoid cycle with logosInquiryVerseThematicV1). */
const JOHN_19_BLOOD_WATER_RE =
  /(옆구리|창에?\s*찔|피와?\s*물|blood\s*and\s*water|side\s*pierc)/i;
const PASSION_CROWN_RE = /(가시\s*면류관|면류관|가시\s*관|crown\s*of\s*thorns)/i;
/** Self-identifying crown-of-thorns forms — no extra 십자가/복음 키워드 required. */
const PASSION_CROWN_SPECIFIC_RE = /(가시\s*면류관|가시\s*관|crown\s*of\s*thorns)/i;
const PASSION_TWO_CRIMINALS_RE =
  /(죄수|강도|도적|옆에\s*못박|같이\s*못박|회개한\s*강도|penitent\s*thief|two\s*thieves|two\s*criminals)/i;
const GOSPEL_CONTEXT_RE =
  /(예수|그리스도|십자가|수난|passion|마태|마가|누가|요한|matt\.?\s*27|mark\.?\s*15|luke\.?\s*23|john\.?\s*19)/i;
const REV21_RE = /(?:계시록|요한계시록|rev\.?)\s*21|새\s*하늘|새\s*땅/i;
const ANTICHRIST_RE = /(666|적그리스도|antichrist)/i;
const GEMATRIA_RE =
  /게마트리아|gematria|수치\s*의미|666\s*의미|수학화|원어.*수학|수학.*원어|원어를\s*수학/i;

const MATCH_MIN_SCORE = 2;

export type LogosAskConfidenceGateV1 = {
  schema: typeof LOGOS_ASK_CONFIDENCE_GATE_SCHEMA;
  allow_curated_thematic: boolean;
  allow_reading_pack: boolean;
  allow_scholar_compose: boolean;
  route_band: LogosAskRouteBandV1;
  route_band_label_ko: string;
  /** Product-visible trust grade — always present; matches route_band honesty. */
  trust_face_ko: string;
  /**
   * Optional soft meaning-audit overlay (rule/lexical only).
   * Never fabricates transformer NLI scores.
   */
  soft_meaning_audit?: LogosAskSoftMeaningAuditV1;
  /** Always HOLD on Ask surface (machine); public face soft copy. */
  send_gate_line_ko: "연구 전용 · 연구 범위 안내";
  hub_id: string | null;
  hub_score: number;
  reasons: string[];
  research_only: true;
  send_gate: "HOLD";
  non_gating: true;
};

export type LogosAskSoftMeaningAuditV1 = {
  schema: "logos_ask_meaning_audit_soft_v1";
  verifier_kind: "rule_overlap_quote_hash_not_nli";
  weak_flag: boolean;
  rule_label: "entail" | "partial" | "fail" | "stub";
  note_ko: string;
};

export type LogosAskHubScoreHitV1 = {
  hub: Golden200HubEntryV1 | null;
  score: number;
};

export function scoreBestGoldenHub(
  query: string,
  registry = getSyncGolden200Registry(),
): LogosAskHubScoreHitV1 {
  let best: Golden200HubEntryV1 | null = null;
  let bestScore = 0;
  for (const entry of registry.entries) {
    const score = scoreGoldenHubEntry(entry, query);
    if (score > bestScore) {
      bestScore = score;
      best = entry;
    }
  }
  if (bestScore < MATCH_MIN_SCORE) return { hub: null, score: bestScore };
  return { hub: best, score: bestScore };
}

function hasSpecificThematicMarker(query: string, _verseRefs: string[]): boolean {
  void _verseRefs;
  const q = query.trim();
  if (!q) return false;
  // Hub MATCH_MIN already implies curated; also accept strong local markers.
  if (JOHN_19_BLOOD_WATER_RE.test(q) && GOSPEL_CONTEXT_RE.test(q)) return true;
  if (PASSION_TWO_CRIMINALS_RE.test(q) && GOSPEL_CONTEXT_RE.test(q)) return true;
  if (PASSION_CROWN_SPECIFIC_RE.test(q)) return true;
  if (PASSION_CROWN_RE.test(q) && GOSPEL_CONTEXT_RE.test(q)) return true;
  if (REV21_RE.test(q)) return true;
  if (ANTICHRIST_RE.test(q)) return true;
  if (GEMATRIA_RE.test(q)) return true;
  if (detectPsalm23Topic(q)) return true;
  if (detectJobSufferingTopic(q)) return true;
  if (detectSamsonJudgesTopic(q)) return true;
  if (detectJohn316Topic(q)) return true;
  if (detectRom828Topic(q)) return true;
  if (detectPsalm51Topic(q)) return true;
  return false;
}

function hasPassionCriminalMarkers(query: string): boolean {
  return PASSION_TWO_CRIMINALS_RE.test(query.trim());
}

/**
 * Bare gospel / long-tail theology without specific hub markers —
 * must not steal john19 / passion packs or pretend curated certainty.
 */
export function isBareGospelAmbiguousQuery(query: string, verseRefs: string[] = []): boolean {
  const q = query.trim();
  if (!q) return false;
  if (hasSpecificThematicMarker(q, verseRefs)) return false;
  if (matchGoldenHubQuery(q)) return false;
  if (hasScriptureAnchor(q)) return false;
  if (!BARE_GOSPEL_RE.test(q)) return false;
  // Explicit faith/doctrine stack → soft faith freeform, not bare-ambiguous defer.
  if (EXPLICIT_FAITH_DOCTRINE_RE.test(q.replace(/십자가|cross/gi, " "))) return false;
  // 「십자가의 의미」 / 「예수는 누구」 style — gospel keyword + question shape, no hub.
  return true;
}

/**
 * Faith freeform must not claim curated certainty for bare 십자가/예수 meaning Qs.
 * Defer to general/research freeform + grade only.
 */
export function shouldDeferFaithPackToGeneral(query: string, verseRefs: string[] = []): boolean {
  const q = query.trim();
  if (!q) return false;
  if (hasSpecificThematicMarker(q, verseRefs)) return false;
  if (matchGoldenHubQuery(q)) return false;
  // Bare 십자가 / cross meaning without doctrine stack → general
  if (/십자가|cross/i.test(q) && !EXPLICIT_FAITH_DOCTRINE_RE.test(q.replace(/십자가|cross/gi, " "))) {
    return true;
  }
  // Bare 「면류관」/crown without self-identifying 가시·crown-of-thorns → general
  // (do not steal passion_crown curated; do not fall to empty G3 without grade path).
  if (
    /(면류관|crown)/i.test(q) &&
    !PASSION_CROWN_SPECIFIC_RE.test(q) &&
    !EXPLICIT_FAITH_DOCTRINE_RE.test(q)
  ) {
    return true;
  }
  return isBareGospelAmbiguousQuery(q, verseRefs) && !EXPLICIT_FAITH_DOCTRINE_RE.test(q);
}

function pack(
  partial: Omit<
    LogosAskConfidenceGateV1,
    | "schema"
    | "research_only"
    | "send_gate"
    | "non_gating"
    | "route_band_label_ko"
    | "trust_face_ko"
    | "send_gate_line_ko"
  > & { soft_meaning_audit?: LogosAskSoftMeaningAuditV1 },
): LogosAskConfidenceGateV1 {
  const wrongPack = (partial.reasons ?? []).some((r) => /wrong_pack/i.test(String(r || "")));
  let trust_face_ko = wrongPack
    ? "연구 범위 안내 · 주제 불일치 가능 — 일반 참고만"
    : LOGOS_ASK_ROUTE_BAND_LABEL_KO[partial.route_band];
  const soft = partial.soft_meaning_audit;
  if (soft?.weak_flag && !wrongPack) {
    // Honest soft overlay — never claims transformer NLI / product entail.
    trust_face_ko = `${trust_face_ko} · 규칙 의미감사 약함(≠NLI)`;
  }
  return {
    schema: LOGOS_ASK_CONFIDENCE_GATE_SCHEMA,
    research_only: true,
    send_gate: "HOLD",
    non_gating: true,
    route_band_label_ko: LOGOS_ASK_ROUTE_BAND_LABEL_KO[partial.route_band],
    trust_face_ko,
    send_gate_line_ko: "연구 전용 · 연구 범위 안내",
    ...partial,
  };
}

/**
 * Attach optional soft meaning-audit signal into confidence gate (honest, ≠ fake NLI).
 */
export function withSoftMeaningAuditSignalV1(
  gate: LogosAskConfidenceGateV1,
  soft: Omit<LogosAskSoftMeaningAuditV1, "schema" | "verifier_kind" | "note_ko"> & {
    note_ko?: string;
  },
): LogosAskConfidenceGateV1 {
  const soft_meaning_audit: LogosAskSoftMeaningAuditV1 = {
    schema: "logos_ask_meaning_audit_soft_v1",
    verifier_kind: "rule_overlap_quote_hash_not_nli",
    weak_flag: Boolean(soft.weak_flag),
    rule_label: soft.rule_label,
    note_ko:
      soft.note_ko ??
      "규칙·어휘 겹침 의미감사만 — transformer NLI / 교리 진리 점수 아님",
  };
  return pack({
    allow_curated_thematic: gate.allow_curated_thematic,
    allow_reading_pack: gate.allow_reading_pack,
    allow_scholar_compose: gate.allow_scholar_compose,
    route_band: gate.route_band,
    hub_id: gate.hub_id,
    hub_score: gate.hub_score,
    reasons: [...gate.reasons, soft.weak_flag ? "soft_meaning_audit_weak" : "soft_meaning_audit_ok"],
    soft_meaning_audit,
  });
}

/**
 * Confidence gate BEFORE narrative — curated vs general+grade spine.
 */
export function evaluateLogosAskConfidenceGateV1(
  query: string,
  verseRefs: string[] = [],
): LogosAskConfidenceGateV1 {
  const q = query.trim();
  const reasons: string[] = [];
  if (!q) {
    return pack({
      allow_curated_thematic: false,
      allow_reading_pack: false,
      allow_scholar_compose: false,
      route_band: "general",
      hub_id: null,
      hub_score: 0,
      reasons: ["empty_query"],
    });
  }

  const { hub, score } = scoreBestGoldenHub(q);
  const hubId = hub?.hub_id ?? null;

  // Wrong-pack defense: Eve/rib + 네피림 dual ask must not claim curated Gen.2/Gen.6 certainty.
  if (isEveRibVsNephilimCollisionQuery(q)) {
    reasons.push("wrong_pack_risk:eve_rib_vs_nephilim");
    return pack({
      allow_curated_thematic: false,
      allow_reading_pack: false,
      allow_scholar_compose: false,
      route_band: "general",
      hub_id: null,
      hub_score: 0,
      reasons,
    });
  }

  // Wrong-pack defense: john19 must never be curated when criminal markers present.
  if (hubId === "john19_blood_water" && hasPassionCriminalMarkers(q)) {
    reasons.push("wrong_pack_risk:passion_two_criminals_vs_john19");
    return pack({
      allow_curated_thematic: false,
      allow_reading_pack: false,
      allow_scholar_compose: false,
      route_band: "general",
      hub_id: null,
      hub_score: 0,
      reasons,
    });
  }

  if (hub && score >= MATCH_MIN_SCORE) {
    reasons.push(`hub_match:${hub.hub_id}:score=${score}`);
    return pack({
      allow_curated_thematic: true,
      allow_reading_pack: true,
      allow_scholar_compose: true,
      route_band: "curated",
      hub_id: hub.hub_id,
      hub_score: score,
      reasons,
    });
  }

  if (hasSpecificThematicMarker(q, verseRefs)) {
    reasons.push("specific_thematic_marker");
    return pack({
      allow_curated_thematic: true,
      allow_reading_pack: true,
      allow_scholar_compose: true,
      route_band: "curated",
      hub_id: hubId,
      hub_score: score,
      reasons,
    });
  }

  if (hasScriptureAnchor(q)) {
    reasons.push("scripture_anchor_soft");
    return pack({
      allow_curated_thematic: false,
      allow_reading_pack: false,
      allow_scholar_compose: false,
      route_band: "soft",
      hub_id: null,
      hub_score: score,
      reasons,
    });
  }

  if (shouldDeferFaithPackToGeneral(q, verseRefs) || isBareGospelAmbiguousQuery(q, verseRefs)) {
    reasons.push("bare_gospel_or_longtail_low_confidence");
    return pack({
      allow_curated_thematic: false,
      allow_reading_pack: false,
      allow_scholar_compose: false,
      route_band: "general",
      hub_id: null,
      hub_score: score,
      reasons,
    });
  }

  if (EXPLICIT_FAITH_DOCTRINE_RE.test(q)) {
    reasons.push("explicit_faith_soft");
    return pack({
      allow_curated_thematic: false,
      allow_reading_pack: false,
      allow_scholar_compose: false,
      route_band: "soft",
      hub_id: null,
      hub_score: score,
      reasons,
    });
  }

  reasons.push("fallback_general");
  return pack({
    allow_curated_thematic: false,
    allow_reading_pack: false,
    allow_scholar_compose: false,
    route_band: "general",
    hub_id: null,
    hub_score: score,
    reasons,
  });
}
