/**
 * Ask BIB-DYN pattern oracle — research_only · SEND HOLD · prediction forbidden.
 * Opt-in drawer remains available; geo/empire/future intents also drive *primary* Ask
 * answers via the same fixture pack (not softmatch wisdom essays).
 */
import pack from "@/data/logos_bib_dyn_pattern_ask_optin_pack_v1.json";

export type BibDynPatternMatchV1 = {
  pattern_id?: string | null;
  label?: string | null;
  cosine_similarity?: number | null;
  phase_template?: string | null;
  representative_verses?: string[];
};

export type BibDynPatternPacketV1 = {
  packet_id: string;
  match_needles: string[];
  question: string;
  gate_status: string;
  gate_reason_codes?: string[];
  harness_mode?: string | null;
  min_cosine_threshold?: number | null;
  scores_are_illustrative_not_semantic?: boolean;
  top_matches: BibDynPatternMatchV1[];
  phase_narrative?: {
    summary?: string | null;
    assembled_phases?: string[];
    forbidden_misread?: string | null;
  } | null;
  source_artifact_schema?: string;
};

export type BibDynPatternPackV1 = {
  schema: string;
  research_only: boolean;
  non_gating: boolean;
  send_gate: string;
  prediction_claims?: string;
  claim_allowed?: boolean;
  track_a_bridge?: boolean;
  ask_default_merged: boolean;
  opt_in_only?: boolean;
  product_all_ok?: boolean;
  harness_label?: string;
  banner_ko?: string;
  reproduce_command?: string;
  artifact_pointer?: string;
  packets: BibDynPatternPacketV1[];
};

export const BIB_DYN_PATTERN_OPTIN_PARAM = "bib_dyn_pattern";

/** Studio / freeform preset when pattern packet drives primary Ask answer. */
export const BIB_DYN_ASK_PRIMARY_PRESET_ID = "dynamic_bib_dyn_pattern" as const;
export const BIB_DYN_ASK_PRIMARY_QUERY_MODE =
  "inquiry_thematic_bib_dyn_pattern" as const;

export const BIB_DYN_PRIMARY_BANNER_KO =
  "패턴 연구 · 예측·매매 아님 · 연구 참고" as const;

/** Nation / empire / hegemony markers (KO+EN). */
const GEO_NATION_RE =
  /미국|중국|미중|미\s*[·･・]?\s*중|china|america|\busa?\b|russia|러시아|로마|rome|바벨론|babylon|제국|empire|패권|hegemon|imperial|nation|국가|열강|초강대/i;

/** Future / war / rise-fall event markers that pair with nation intent. */
const GEO_EVENT_RE =
  /미래|전쟁|war|충돌|갈등|패권|몰락|hubris|fall|흥망|지정학|geopolit|상승|쇠퇴|어떻게\s*될|전망|붕괴|심판|judgment|ascend|collapse/i;

/**
 * Geopolitical / nation / empire / future pattern intent — routes to BIB-DYN
 * primary Ask (not G3 wisdom/anxiety softmatch essays).
 */
export function isGeoNationEmpirePatternIntent(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  return GEO_NATION_RE.test(q) && GEO_EVENT_RE.test(q);
}

export function isBibDynPatternAskOptInEnabled(
  searchParams: { get: (k: string) => string | null } | null | undefined,
  localOn: boolean,
): boolean {
  if (localOn) return true;
  const v = (searchParams?.get(BIB_DYN_PATTERN_OPTIN_PARAM) || "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "on" || v === "yes";
}

export function loadBibDynPatternAskOptInPack(): BibDynPatternPackV1 {
  return pack as unknown as BibDynPatternPackV1;
}

function scorePacketNeedles(queryLower: string, packet: BibDynPatternPacketV1): number {
  let score = 0;
  for (const n of packet.match_needles || []) {
    const needle = String(n || "").toLowerCase();
    if (needle && queryLower.includes(needle)) score += 1;
  }
  return score;
}

/** Score user query against fixture needles; return best packet or null if weak. */
export function matchBibDynPatternOptInPacket(
  query: string,
  packDoc: BibDynPatternPackV1 = loadBibDynPatternAskOptInPack(),
  minScore = 1,
): BibDynPatternPacketV1 | null {
  const q = (query || "").toLowerCase();
  if (!q.trim()) return null;
  let best: BibDynPatternPacketV1 | null = null;
  let bestScore = 0;
  for (const p of packDoc.packets || []) {
    const score = scorePacketNeedles(q, p);
    if (score > bestScore) {
      bestScore = score;
      best = p;
    }
  }
  return bestScore >= minScore ? best : null;
}

/**
 * Primary Ask router: needle hit, or geo/nation/future intent → empire/babylon pack.
 * Prefer REJECTED_INTENT (trading) when that packet wins needles.
 */
export function matchBibDynPatternForAskPrimary(
  query: string,
  packDoc: BibDynPatternPackV1 = loadBibDynPatternAskOptInPack(),
): BibDynPatternPacketV1 | null {
  const q = (query || "").trim();
  if (!q) return null;

  const needleHit = matchBibDynPatternOptInPacket(q, packDoc, 1);
  if (needleHit?.gate_status === "REJECTED_INTENT") return needleHit;

  if (needleHit?.gate_status === "PASSED" && (needleHit.top_matches || []).length > 0) {
    return needleHit;
  }

  if (isGeoNationEmpirePatternIntent(q)) {
    const babylon = (packDoc.packets || []).find(
      (p) => p.packet_id === "valid_babylon" && p.gate_status === "PASSED",
    );
    if (babylon && (babylon.top_matches || []).length > 0) return babylon;
  }

  // Opt-in / URL mode: return weak REJECTED_LOW_SIMILARITY / empty PASSED only if needle matched
  if (needleHit) return needleHit;
  return null;
}

/** Representative verses from pattern matches (citation lock for primary panel). */
export function extractBibDynPatternVerseRefs(
  packet: BibDynPatternPacketV1 | null | undefined,
  max = 12,
): string[] {
  if (!packet) return [];
  const out: string[] = [];
  for (const m of packet.top_matches || []) {
    for (const v of m.representative_verses || []) {
      const t = String(v || "").trim();
      if (t && !out.includes(t)) out.push(t);
      if (out.length >= max) return out;
    }
  }
  return out;
}

/**
 * Primary Ask answer body from fixture packet — patterns + phases + HYPO walls.
 * Never prediction / Track A / calendar geopolitics forecast.
 */
export function buildBibDynPrimaryAnswerKo(
  packet: BibDynPatternPacketV1,
  query: string,
): string {
  const qShort = query.trim().slice(0, 96);
  const matches = (packet.top_matches || []).slice(0, 3);
  const verses = extractBibDynPatternVerseRefs(packet, 8);
  const phases =
    (packet.phase_narrative?.assembled_phases || []).filter(Boolean).length > 0
      ? (packet.phase_narrative?.assembled_phases || []).filter(Boolean)
      : matches.map((m) => m.phase_template).filter(Boolean);

  if (packet.gate_status === "REJECTED_INTENT") {
    return [
      "### 짧은 답",
      `「${qShort}」→ 패턴 연구 레인에서 의도 거절 (매매·예측 신호 금지).`,
      "",
      "### 다음에 할 일",
      "- 매수/매도·가격 전망이 아니라, 성경 서사 모티프·국면 어휘로 다시 물어 주세요.",
      "- 예: 「바벨론 제국의 교만과 몰락 국면 어휘」, 「언약 파기와 유배 모티프」",
      "",
      "### 한계",
      `- ${BIB_DYN_PRIMARY_BANNER_KO}`,
      "- 연구 참고 · 예보·투자 단정 아님",
    ].join("\n");
  }

  if (packet.gate_status !== "PASSED" || matches.length === 0) {
    return [
      "### 짧은 답",
      `「${qShort}」→ 명확한 패턴 매칭이 없어 긴 답을 만들지 않습니다.`,
      "",
      "### 다음에 할 일",
      "- 권·장·구절 또는 제국/언약/유배 등 패턴 주제로 좁혀 주세요.",
      "",
      "### 한계",
      `- ${BIB_DYN_PRIMARY_BANNER_KO}`,
    ].join("\n");
  }

  const matchLines = matches.map((m, i) => {
    const phase = m.phase_template ? ` · ${m.phase_template}` : "";
    const refs = (m.representative_verses || []).slice(0, 3).join(", ");
    const label = String(m.label || "").trim() || "관련 패턴";
    return `${i + 1}. **${label}**${phase}${refs ? ` · ${refs}` : ""}`;
  });

  return [
    "### 짧은 답",
    `「${qShort}」→ 성경 서사 패턴 연구 매칭입니다. 현대 미·중 일정·승패 예보가 아닙니다.`,
    "",
    "### 신뢰 등급",
    "패턴 연구 · 문헌 축 가설 · 교리·투자 확정 아님",
    "",
    "### 근거 본문 (패턴 대표 구절)",
    verses.length > 0
      ? verses.join(" · ")
      : "대표 구절 없음 — 추가 구체화 필요",
    "",
    "### 패턴 후보",
    ...matchLines,
    "",
    "### 국면 사슬",
    phases.length > 0 ? phases.join(" · ") : "(국면 사슬 없음)",
    "",
    "### 한계",
    packet.phase_narrative?.summary
      ? String(packet.phase_narrative.summary).slice(0, 420)
      : "문헌 축 발견만 · 현대 국가 일정 예보 금지",
    packet.phase_narrative?.forbidden_misread
      ? `- 주의: ${packet.phase_narrative.forbidden_misread}`
      : "- 금지: 모티프를 현대 국가 붕괴 예보로 읽기",
    "- 연구 참고 · 예보·투자 단정 아님",
  ].join("\n");
}
