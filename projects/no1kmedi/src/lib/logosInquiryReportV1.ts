/** Logos inquiry report v1 — Standard tier S1-S5 (mirrors scripts/core/logos_inquiry_report_v1.py) */
import { createHash } from "node:crypto";

import type { StudioQueryPayload } from "./logosResearchStudioV1";
import type { ConflictContextResult } from "./logosStudioConflictBridgeV1";
import {
  evaluateLogosTextMvpIntake,
  type LogosTextMvpIntakeSummary,
} from "./logosResearchTextMvpV1";
import type { SasangRegimeHintBTrack } from "./logosInquiryFreezeMetaV1";
import { filterStudioBoilerplateLines, isStudioBoilerplateKo } from "./logosStudioBoilerplateV1";
import {
  firstNonStubLine,
  isPublicS4StubPhrase,
  PUBLIC_S4_STUB_PHRASE_RE,
} from "./logosInquiryPublicS4FilterV1";

export type LogosInquiryReportV1 = {
  schema: "logos_inquiry_report_v1";
  version: string;
  tier: "standard";
  output_format: "inquiry_report_v1";
  generated_at_utc: string;
  research_only: boolean;
  non_gating: boolean;
  send_gate: string;
  query: string;
  preset_id?: string | null;
  query_mode?: string | null;
  intake: LogosTextMvpIntakeSummary;
  sections: {
    S1: {
      section_id: "S1_citation_lock";
      title_ko: string;
      verse_refs: string[];
      citation_lock_anchors: string[];
      security_note_ko: string;
    };
    S2: {
      section_id: "S2_lexicon_hash";
      title_ko: string;
      lemma_edge_line_count: number | null;
      min_line_count_floor: number;
      floor_pass: boolean;
      freeze_manifest_pointer: string;
      manifest_sha256: string | null;
      lemma_edges_sha256: string;
      sidecar_corpus_sha256: string;
      path_token_preview: string[];
      security_note_ko: string;
    };
    S3: {
      section_id: "S3_context_divergence";
      title_ko: string;
      groups: Array<Record<string, unknown>>;
      note_ko: string;
      regime_hint_b_track?: SasangRegimeHintBTrack | null;
    };
    S4: {
      section_id: "S4_dynamic_synthesis";
      title_ko: string;
      body_ko: string;
      bullets_ko: string[];
      streaming_deferred?: "P0-1b" | "active";
      format_gate?: {
        applied: boolean;
        missing_sections: string[];
        recomposed: boolean;
      };
    };
    S5: {
      section_id: "S5_jema_integrity_signoff";
      title_ko: string;
      signoff_status?: "provisional" | "final";
      chain_exit_code: number;
      artifact_path: string;
      sections_payload_sha256: string | null;
      freeze_verify_command: string;
      signed_at_utc: string;
      note_ko?: string;
    };
  };
  governance: {
    disclaimer_ko: string;
    forbidden_claims: string[];
    quality_basis_ko: string;
  };
  evidence_confidence?: StudioQueryPayload["evidence_confidence"] | null;
  azure_distill_meta?: StudioQueryPayload["azure_distill_meta"] | null;
};

export type FreezeLexiconMeta = {
  lemma_edge_line_count: number | null;
  min_line_count_floor: number;
  floor_pass: boolean;
  freeze_manifest_pointer: string;
  manifest_sha256: string | null;
  lemma_edges_sha256: string;
  sidecar_corpus_sha256: string;
};

export const DEFAULT_FREEZE_LEXICON_META: FreezeLexiconMeta = {
  lemma_edge_line_count: 298984,
  min_line_count_floor: 290000,
  floor_pass: true,
  freeze_manifest_pointer: "docs/final/artifacts/logos_corpus_knowledge_freeze_manifest_v1_latest.json",
  manifest_sha256: null,
  lemma_edges_sha256: "b0f33b703e88d986a75baa446571242d4f097567b4eadd68b061d857685446c0",
  sidecar_corpus_sha256: "e9cdd90c278b37a0316235438a9dfe187543c66b966ac14c6c5ac19c23178c32",
};

const FREEZE_ARTIFACT = "reports/logos_inquiry_report_schema_freeze_v1_latest.json";

function stripHypo(text: string): string {
  return (text || "").replace(/^\[HYPO\]\s*/i, "").replace(/\[HYPO\]\s*/g, "").trim();
}

const GEMATRIA_BULLET_RE =
  /combined_sum|vector_4d|hub_score|state16|Gematria_Pin|topology pin|mispar_/i;

const PUBLIC_LEAK_RE =
  /lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절|Path\s*envelope|orphan\s*veto|Gematria_Pin/i;

export { isPublicS4StubPhrase, PUBLIC_S4_STUB_PHRASE_RE } from "./logosInquiryPublicS4FilterV1";

function firstNonStub(lines: string[]): string {
  return firstNonStubLine(lines);
}

function prioritizeVerseRefsForQuery(query: string, verseRefs: string[]): string[] {
  const q = (query || "").trim();
  const refs = [...(verseRefs || [])].map((r) => String(r).trim()).filter(Boolean);
  if (!q) return refs;

  const isPsalm23Query =
    /시편\s*23|psalm\s*23|ps\.?\s*23/i.test(q) ||
    (/(시편|psalm)/i.test(q) && /목자|shepherd/i.test(q));

  if (isPsalm23Query) {
    const ps23 = refs.filter((r) => /^Ps\.23/i.test(r.replace(/\s/g, "")));
    const rest = refs.filter((r) => !/^Ps\.23/i.test(r.replace(/\s/g, "")));
    if (ps23.length) return [...ps23, ...rest];
    const withoutJobStub = refs.filter((r) => !/^Job\./i.test(r.replace(/\s/g, "")));
    return ["Ps.23.1", "Ps.23.4", ...withoutJobStub];
  }

  return refs;
}

function coreClaimFallback(query: string, verseRefs: string[]): string {
  const refs = prioritizeVerseRefsForQuery(query, verseRefs);
  const ps23 = refs.filter((r) => /^Ps\.23/i.test(r.replace(/\s/g, "")));
  if (ps23.length) {
    return `시편 23편(${ps23.slice(0, 2).join(" · ")})의 목자·신뢰·길 안내 이미지를 citation lock 앵커 중심으로 해석합니다.`;
  }
  if (refs.length) {
    return `${refs.slice(0, 2).join(" · ")} 앵커 구절을 중심으로 질문의 논지를 정리합니다.`;
  }
  return "질문의 중심 논지를 citation lock 앵커 기준으로 해석합니다.";
}

function scrubStubFromFiveSectionBody(body: string, query: string, verseRefs: string[]): string {
  const raw = normalizeWhitespace(body || "");
  if (!raw) return raw;

  const sectionRe = /(###\s*핵심\s*주장\s*\n)([\s\S]*?)(?=\n###\s|$)/i;
  const match = sectionRe.exec(raw);
  if (!match) return raw;

  const heading = match[1];
  const coreBody = match[2].trim();
  const coreLines = coreBody.split("\n").map((l) => l.trim()).filter(Boolean);
  const cleanCore = firstNonStub(coreLines);
  if (cleanCore && !isPublicS4StubPhrase(cleanCore)) {
    return raw.replace(sectionRe, `${heading}${cleanCore}\n`);
  }

  const fallback = coreClaimFallback(query, verseRefs);
  return raw.replace(sectionRe, `${heading}${fallback}\n`);
}

function leadAnswerSection(text: string): string {
  const raw = (text || "").trim();
  return (raw.split(/(?:^|\n|\s)---(?:\s|\n)|###\s*Reading pack/i)[0] ?? raw).trim();
}

function splitBullets(text: string): string[] {
  const bullets: string[] = [];
  for (const line of leadAnswerSection(text).split("\n")) {
    const m = line.trim().match(/^[-*•]\s+(.+)$/);
    if (m) {
      const item = stripHypo(m[1]);
      if (!GEMATRIA_BULLET_RE.test(item)) bullets.push(item);
    }
  }
  return bullets;
}

function normalizeWhitespace(text: string): string {
  return (text || "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/** Public S4 body — strip internal research tags (display/scoring parity with Python lib). */
export function stripPublicResearchTagsForS4(body: string): string {
  return normalizeWhitespace(
    (body || "")
      .replace(/\[HYPO\]\s*/gi, "")
      .replace(/\[NON_GATING\]\s*/gi, "")
      .replace(/\bresearch_only\b/gi, "")
      .replace(/\bsend_gate\s*:\s*\w+/gi, ""),
  );
}

function stripPublicLeakSegments(text: string): string {
  return normalizeWhitespace(
    (text || "")
      .replace(/(?:^|\n)\s*Lemma\s*연결\s*이웃\s*구절[\s\S]*?(?=(?:\n###\s*Reading pack)|$)/gi, "\n")
      .replace(/lemma:gnosis:[^\s,;]+/gi, "")
      .replace(/shared_lemma=\d+/gi, "")
  );
}

export function sanitizeInquiryS4ForPublic(body: string): {
  body: string;
  leak_detected: boolean;
  fallback_applied: boolean;
} {
  const raw = String(body || "").trim();
  const leak_detected = PUBLIC_LEAK_RE.test(raw);
  if (!raw) {
    return {
      body: "Citation lock 기반 해석 요약을 준비 중입니다. 구절 앵커 중심으로 간단히 다시 질문해 주세요. [NON_GATING]",
      leak_detected: false,
      fallback_applied: true,
    };
  }
  const cleaned = stripPublicLeakSegments(raw);
  if (!leak_detected) {
    return { body: cleaned || raw, leak_detected: false, fallback_applied: false };
  }
  if (cleaned.length >= 120) {
    return { body: cleaned, leak_detected: true, fallback_applied: false };
  }
  return {
    body:
      "Citation lock 앵커 구절 기준의 해석 요약만 공개합니다. 내부 lemma raw/토큰 덤프는 숨김 처리되었습니다. 핵심 구절(예: Dan.2.10-19)의 의미 축을 지정해 다시 질문해 주세요. [NON_GATING]",
    leak_detected: true,
    fallback_applied: true,
  };
}

const FIVE_SECTION_TITLES = [
  "### 핵심 주장",
  "### 근거 구절",
  "### 반증·대안",
  "### 한계·주의",
  "### 다음 행동 제안",
] as const;

function splitSentences(text: string): string[] {
  return (text || "")
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?。！？])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}


function extractRefsFromBody(body: string): string[] {
  const refs = new Set<string>();
  const refRe = /\b(?:[1-3]\s*)?[A-Za-z가-힣]+\.?\s*\d{1,3}(?::\d{1,3}(?:-\d{1,3})?)?/g;
  for (const m of body.matchAll(refRe)) {
    const ref = String(m[0] || "").replace(/\s+/g, " ").trim();
    if (ref) refs.add(ref);
  }
  return Array.from(refs);
}

function buildFiveSectionS4(input: {
  body: string;
  bullets: string[];
  verseRefs: string[];
  query?: string;
}): {
  body: string;
  missing_sections: string[];
  recomposed: boolean;
} {
  const query = input.query ?? "";
  const body = normalizeWhitespace(input.body || "");
  const bullets = (input.bullets || [])
    .map((b) => b.trim())
    .filter((b) => b && !isPublicS4StubPhrase(b));
  const verseRefs = prioritizeVerseRefsForQuery(query, input.verseRefs ?? []);
  const hasAllSections = FIVE_SECTION_TITLES.every((title) => body.includes(title));
  if (hasAllSections) {
    return {
      body: scrubStubFromFiveSectionBody(body, query, verseRefs),
      missing_sections: [],
      recomposed: false,
    };
  }

  const lines = body.split("\n").map((line) => line.trim()).filter(Boolean);
  const sentences = splitSentences(body).filter((s) => !isPublicS4StubPhrase(s));
  const refs = (verseRefs.length ? verseRefs : extractRefsFromBody(body)).slice(0, 4);
  const coreClaim =
    firstNonStub([
      ...bullets,
      ...sentences,
      ...lines,
    ]) || coreClaimFallback(query, refs);
  const evidenceLine =
    refs.length > 0
      ? refs.map((ref) => `- ${ref}`).join("\n")
      : "- 명시 구절이 부족해 재질의가 필요합니다. (권·장·절 앵커 권장)";
  const counterLine =
    firstNonStub(bullets.slice(1).concat(sentences.slice(1))) ||
    "대안 해석 가능성을 병기하며 단일 해석을 절대화하지 않습니다.";
  const limitLine =
    firstNonStub(bullets.slice(2).concat(sentences.slice(2))) ||
    "본 응답은 연구 요약이며 교리 확정/실행 지시가 아닙니다.";
  const actionLine =
    firstNonStub(bullets.slice(3)) ||
    "핵심 구절 1~2개를 지정해 재질문하면 문맥-반증 비교를 더 정밀화할 수 있습니다.";
  const recomposed = normalizeWhitespace(
    [
      "### 핵심 주장",
      coreClaim,
      "",
      "### 근거 구절",
      evidenceLine,
      "",
      "### 반증·대안",
      counterLine,
      "",
      "### 한계·주의",
      limitLine,
      "",
      "### 다음 행동 제안",
      actionLine,
    ].join("\n"),
  );
  return {
    body: recomposed,
    missing_sections: FIVE_SECTION_TITLES.filter((title) => !body.includes(title)),
    recomposed: true,
  };
}

export function applyInquiryS4QualityGate(input: {
  body: string;
  bullets: string[];
  verseRefs: string[];
  query?: string;
}): {
  body: string;
  leak_detected: boolean;
  fallback_applied: boolean;
  missing_sections: string[];
  recomposed: boolean;
} {
  const query = input.query ?? "";
  const verseRefs = prioritizeVerseRefsForQuery(query, input.verseRefs ?? []);
  const sanitized = sanitizeInquiryS4ForPublic(input.body);
  const composed = buildFiveSectionS4({
    body: sanitized.body,
    bullets: (input.bullets ?? []).filter((b) => !isPublicS4StubPhrase(b)),
    verseRefs,
    query,
  });
  return {
    body: stripPublicResearchTagsForS4(
      scrubStubFromFiveSectionBody(composed.body, query, verseRefs),
    ),
    leak_detected: sanitized.leak_detected,
    fallback_applied: sanitized.fallback_applied,
    missing_sections: composed.missing_sections,
    recomposed: composed.recomposed,
  };
}

function ensureFiveSectionS4Draft(input: {
  body: string;
  bullets: string[];
  verseRefs: string[];
  query?: string;
}): string {
  const built = buildFiveSectionS4(input);
  return built.body;
}

function extractAnchors(payload: StudioQueryPayload): string[] {
  const anchors: string[] = [];
  const seen = new Set<string>();
  const conflict = payload.conflict_context as Extract<ConflictContextResult, { ok: true }> | null;
  if (conflict?.groups) {
    for (const group of conflict.groups) {
      for (const school of group.schools ?? []) {
        for (const anchor of school.citation_lock_anchors ?? []) {
          const t = String(anchor).trim();
          if (t && !seen.has(t)) {
            seen.add(t);
            anchors.push(t);
          }
        }
      }
    }
  }
  for (const ref of payload.path?.verse_refs ?? []) {
    const t = String(ref).trim();
    if (t && !seen.has(t)) {
      seen.add(t);
      anchors.push(t);
    }
  }
  return anchors;
}

function buildSchoolGroups(payload: StudioQueryPayload): Array<Record<string, unknown>> {
  const conflict = payload.conflict_context as Extract<ConflictContextResult, { ok: true }> | null;
  if (!conflict?.groups?.length) return [];
  return conflict.groups.map((group) => ({
    conflict_group_id: group.conflict_group_id,
    lexicon_base: group.lexicon_base,
    school_count: group.school_count ?? group.schools?.length ?? 0,
    schools: (group.schools ?? []).map((school) => ({
      school_tier: school.school_tier,
      interpretation_ko: stripHypo(school.interpretation_ko ?? ""),
      verse_refs: school.verse_refs ?? [],
      citation_lock_anchors: school.citation_lock_anchors ?? [],
      traditions: school.traditions ?? [],
    })),
  }));
}

function pathTokenPreview(payload: StudioQueryPayload, cap = 16): string[] {
  const tokens: string[] = [];
  const seen = new Set<string>();
  const push = (t: string) => {
    const v = t.trim();
    if (!v || seen.has(v)) return;
    seen.add(v);
    tokens.push(v);
  };

  for (const raw of [...(payload.path?.node_ids ?? []), ...(payload.path?.steps ?? [])]) {
    const t = String(raw).trim();
    if (/^[A-Za-z0-9]+\.\d/.test(t)) push(t);
    else if (/^lemma_/.test(t) || t.startsWith("node:")) push(t.replace(/^node:/, ""));
    else if (/gematria/i.test(t)) push(t);
    if (tokens.length >= cap) break;
  }

  for (const ref of payload.path?.verse_refs ?? []) {
    if (tokens.length >= cap) break;
    const verse = String(ref).trim();
    if (!verse) continue;
    const pin = createHash("sha256").update(`gematria_pin:${verse}`, "utf8").digest("hex").slice(0, 12);
    push(`Gematria_Pin:${pin}`);
  }

  return tokens.slice(0, cap);
}

function sortKeysDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeysDeep);
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    return Object.keys(obj)
      .sort()
      .reduce<Record<string, unknown>>((acc, key) => {
        acc[key] = sortKeysDeep(obj[key]);
        return acc;
      }, {});
  }
  return value;
}

function sha256Sections(s1s4: Record<string, unknown>): string {
  const canonical = JSON.stringify(sortKeysDeep(s1s4));
  return createHash("sha256").update(canonical, "utf8").digest("hex");
}

export function buildLogosInquiryReport(
  payload: StudioQueryPayload,
  query: string,
  intake: LogosTextMvpIntakeSummary,
  freezeMeta: FreezeLexiconMeta = DEFAULT_FREEZE_LEXICON_META,
  chainExitCode = 0,
  sasangHint: SasangRegimeHintBTrack | null = null,
): LogosInquiryReportV1 {
  const answer = stripHypo(payload.answer ?? "");
  const verseRefs = (payload.path?.verse_refs ?? []).map((v) => String(v).trim()).filter(Boolean);
  const bullets = filterStudioBoilerplateLines(splitBullets(payload.answer ?? ""));
  if (payload.insight_card?.gap_ko) {
    const gap = stripHypo(payload.insight_card.gap_ko);
    if (!isStudioBoilerplateKo(gap)) bullets.push(gap);
  }

  const s1 = {
    section_id: "S1_citation_lock" as const,
    title_ko: "Citation Lock (구절 인용)",
    verse_refs: verseRefs.slice(0, 24),
    citation_lock_anchors: extractAnchors(payload).slice(0, 24),
    security_note_ko: "canonical verse ref·citation lock 인덱스만 — KRV/31k 원문 전문 노출 금지.",
  };
  const s2 = {
    section_id: "S2_lexicon_hash" as const,
    title_ko: "Lexicon Hash (원어 렉시콘)",
    lemma_edge_line_count: freezeMeta.lemma_edge_line_count,
    min_line_count_floor: freezeMeta.min_line_count_floor,
    floor_pass: freezeMeta.floor_pass,
    freeze_manifest_pointer: freezeMeta.freeze_manifest_pointer,
    manifest_sha256: freezeMeta.manifest_sha256,
    lemma_edges_sha256: freezeMeta.lemma_edges_sha256,
    sidecar_corpus_sha256: freezeMeta.sidecar_corpus_sha256,
    path_token_preview: pathTokenPreview(payload),
    security_note_ko: "29만 행 원문 덤프 금지 — line_count·sha256 pin·경로 토큰 preview만.",
  };
  const s3 = {
    section_id: "S3_context_divergence" as const,
    title_ko: "Context Divergence (맥락/학파 분기)",
    groups: buildSchoolGroups(payload),
    note_ko: "[NON_GATING] conflict_context 기반 — Track A·실매매 트리거 아님.",
    ...(sasangHint ? { regime_hint_b_track: sasangHint } : {}),
  };
  const s4 = {
    section_id: "S4_dynamic_synthesis" as const,
    title_ko: "Dynamic Synthesis (고차원 통찰)",
    body_ko: ensureFiveSectionS4Draft({
      body: answer || "응답 본문을 생성하지 못했습니다.",
      bullets,
      verseRefs,
      query: query.trim(),
    }),
    bullets_ko: bullets.slice(0, 8),
    streaming_deferred: "active" as const,
  };
  const s1s4 = { S1: s1, S2: s2, S3: s3, S4: s4 };
  const signedAt = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const s5 = {
    section_id: "S5_jema_integrity_signoff" as const,
    title_ko: "JEMA Integrity Signoff (무결성 서명)",
    signoff_status: "final" as const,
    chain_exit_code: chainExitCode,
    artifact_path: FREEZE_ARTIFACT,
    sections_payload_sha256: sha256Sections(s1s4),
    freeze_verify_command: "py scripts/check_logos_corpus_knowledge_freeze_manifest_v1.py",
    signed_at_utc: signedAt,
  };

  return {
    schema: "logos_inquiry_report_v1",
    version: "1.0.0",
    tier: "standard",
    output_format: "inquiry_report_v1",
    generated_at_utc: signedAt,
    research_only: payload.research_only ?? true,
    non_gating: payload.non_gating ?? true,
    send_gate: payload.send_gate ?? "HOLD",
    query: query.trim(),
    preset_id: payload.preset_id,
    query_mode: payload.query_mode ?? null,
    intake,
    sections: { ...s1s4, S5: s5 },
    governance: {
      disclaimer_ko:
        "logos inquiry Standard — Track B [HYPO] · research_only · NON_GATING. 의료·진단·투자·실거래 지시가 아닙니다.",
      forbidden_claims: ["무환각 0%", "GPT 대체", "KRV/31k 원문 전체 공개", "투자·실매매 트리거"],
      quality_basis_ko: "eval·Brier·citation lock·freeze pin — 마케팅 환각률 주장 금지.",
    },
    evidence_confidence: payload.evidence_confidence ?? null,
    azure_distill_meta: payload.azure_distill_meta ?? null,
  };
}

export { evaluateLogosTextMvpIntake as evaluateLogosInquiryIntake };
export { enrichLogosResearchQuery, hasScriptureAnchor } from "./logosInquiryQueryEnrichV1";
