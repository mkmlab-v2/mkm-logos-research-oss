/** Commander-facing ask UI — 3-line executive summary (display only, not API schema). */
import type { LogosInquiryReportV1 } from "./logosInquiryReportV1";
import {
  isPublicS4StubPhrase,
  PUBLIC_S4_STUB_PHRASE_RE,
} from "./logosInquiryPublicS4FilterV1";
import type { StreamSnapshot } from "./logosInquiryStreamV1";
import type { SasangRegimeHintBTrack } from "./logosInquiryFreezeMetaV1";
import { detectPsalm23Topic, detectSchoolComparisonIntent } from "./logosInquiryTopicDetectV1";
import { isStudioBoilerplateKo } from "./logosStudioBoilerplateV1";

type InquiryAuxS2 = Pick<LogosInquiryReportV1["sections"]["S2"], "path_token_preview"> | null | undefined;
type InquiryAuxS3 = Pick<LogosInquiryReportV1["sections"]["S3"], "regime_hint_b_track"> | null | undefined;

const META_LINE_RE =
  /^\*\*(Query|Pack|Governance|query_id|utterance_class):/i;

const GEMATRIA_BULLET_RE =
  /combined_sum|vector_4d|hub_score|state16|Gematria_Pin|topology pin|mispar_/i;

/** Azure distill + packs — executive summary uses lead narrative only. */
function executiveBodyForSummary(body: string): string {
  const raw = (body || "").trim();
  if (!raw) return "";
  const beforePack = raw.split(/(?:^|\n|\s)---(?:\s|\n)|###\s*Reading pack/i)[0] ?? raw;
  return beforePack.trim();
}

function stripMarkdownInline(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^#+\s*/, "")
    .trim();
}

export function commanderSummaryLines(
  body: string,
  bullets: string[] = [],
  maxLines = 3,
): string[] {
  const leadBody = executiveBodyForSummary(body);

  const fromBullets = bullets
    .map((b) => stripMarkdownInline(b))
    .filter(
      (b) =>
        b.length > 8 &&
        !META_LINE_RE.test(b) &&
        !isStudioBoilerplateKo(b) &&
        !GEMATRIA_BULLET_RE.test(b),
    )
    .slice(0, maxLines);
  if (fromBullets.length > 0 && !leadBody) return fromBullets;

  const lines: string[] = [];
  const chunks = leadBody
    .split(/\n+/)
    .map((p) => stripMarkdownInline(p))
    .filter((p) => p.length > 0);

  for (const chunk of chunks) {
    if (META_LINE_RE.test(chunk) || chunk.startsWith("###") || isStudioBoilerplateKo(chunk)) continue;
    if (GEMATRIA_BULLET_RE.test(chunk)) continue;
    if (chunk.length > 220) {
      const sentences = chunk.split(/(?<=[.!?…])\s+/).filter((s) => s.trim().length > 12);
      for (const sentence of sentences) {
        lines.push(sentence.trim());
        if (lines.length >= maxLines) return lines;
      }
    } else {
      lines.push(chunk);
    }
    if (lines.length >= maxLines) break;
  }

  if (lines.length > 0) return lines.slice(0, maxLines);

  const metaBullets = fromBullets.filter((b) => !/envelope|concordance|citation lock|orphan veto/i.test(b));
  return metaBullets.slice(0, maxLines);
}

export function commanderSummaryText(
  body: string,
  bullets: string[] = [],
  maxLines = 3,
): string {
  return commanderSummaryLines(body, bullets, maxLines).join("\n");
}

/** Public Ask UI — strip internal research tags (display only; API payload unchanged). */
export function stripPublicResearchTags(text: string): string {
  return (text || "")
    .replace(/(?:^|\n)\s*Lemma\s*연결\s*이웃\s*구절[\s\S]*?(?=(?:\n###\s*Reading pack)|$)/gi, "\n")
    .replace(/lemma:gnosis:[^\s,;]+/gi, "")
    .replace(/shared_lemma=\d+/gi, "")
    .replace(/\[HYPO\]\s*/gi, "")
    .replace(/\[NON_GATING\]\s*/gi, "")
    .replace(/\bresearch_only\b/gi, "")
    .replace(/\bsend_gate\s*:\s*\w+/gi, "")
    .replace(/디지털\s*환경에서\s*정보의\s*진실성[^.!?…]*[.!?…]?/gi, "")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

export function splitS4PublicBody(body: string): { narrative: string; readingPack: string } {
  const raw = (body || "").trim();
  if (!raw) return { narrative: "", readingPack: "" };
  const parts = raw.split(/(?:^|\n|\s)---(?:\s|\n)|###\s*Reading pack/i);
  const narrative = stripPublicResearchTags((parts[0] ?? "").trim());
  const readingPackRaw = stripPublicResearchTags(parts.slice(1).join("\n").trim());
  const readingPack = isStudioBoilerplateKo(readingPackRaw) ? "" : readingPackRaw;
  return { narrative, readingPack };
}

const GEMATRIA_OR_META_LINE_RE =
  /combined_sum|vector_4d|hub_score|state16|Gematria_Pin|topology pin|mispar_|lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절|Path\s*envelope|orphan\s*veto|^\*\*(Query|Pack|Governance|query_id|utterance_class):/i;

export { isPublicS4StubPhrase, PUBLIC_S4_STUB_PHRASE_RE };

export function isGematriaOrMetaLine(line: string): boolean {
  const t = (line || "").trim();
  if (!t) return true;
  return GEMATRIA_OR_META_LINE_RE.test(t) || isStudioBoilerplateKo(t) || isPublicS4StubPhrase(t);
}

export type S4PublicSectionV1 = {
  title: string;
  body: string;
};

/** Public S4 — preserve ### section structure for Ask UI (display only). */
export function parseS4PublicSections(body: string, displayQuery?: string): S4PublicSectionV1[] {
  const { narrative } = splitS4PublicBody(body);
  const source = narrative || stripPublicResearchTags(body);
  if (!source) return [];

  const chunks = source.split(/\n(?=###\s+)/).map((c) => c.trim()).filter(Boolean);
  const sections: S4PublicSectionV1[] = [];

  for (const chunk of chunks) {
    const heading = /^###\s*(.+?)(?:\n|$)/.exec(chunk);
    if (!heading) {
      const flat = polishPublicS4SectionBody(chunk, displayQuery);
      if (flat.length > 20 && !isGematriaOrMetaLine(flat)) {
        sections.push({ title: "통찰", body: flat });
      }
      continue;
    }
    const title = stripMarkdownInline(heading[1]);
    const rawBody = chunk.slice(heading[0].length).trim();
    const bodyText = polishPublicS4SectionBody(rawBody, displayQuery);
    if (title || bodyText) {
      sections.push({ title: title || "통찰", body: bodyText });
    }
  }

  if (sections.length) return sections;

  const paragraphs = formatPublicNarrativeParagraphs(body, displayQuery);
  return paragraphs.map((p, i) => ({
    title: i === 0 ? "통찰" : `통찰 ${i + 1}`,
    body: p,
  }));
}

/** Public narrative — paragraph blocks for primary insight UI (display only). */
export function formatPublicNarrativeParagraphs(body: string, displayQuery?: string): string[] {
  const { narrative } = splitS4PublicBody(body);
  const source = narrative || stripPublicResearchTags(body);
  if (!source) return [];

  const polished = polishPublicS4SectionBody(source, displayQuery);
  const blocks = polished.split(/\n{2,}|\n(?=###\s+)/).map((p) => p.trim()).filter(Boolean);
  const paragraphs: string[] = [];

  for (const block of blocks) {
    if (isGematriaOrMetaLine(block)) continue;
    let text = block;
    if (text.startsWith("###")) {
      const lines = text.split(/\n+/).map((l) => l.trim()).filter(Boolean);
      const title = lines[0]?.replace(/^###\s*\d*\.?\s*/, "").trim() ?? "";
      const sectionBody = polishPublicS4SectionBody(lines.slice(1).join("\n"), displayQuery);
      text = [title, sectionBody].filter(Boolean).join(" — ");
    } else {
      text = polishPublicS4SectionBody(text, displayQuery);
    }
    if (text.length > 20 && !isGematriaOrMetaLine(text)) paragraphs.push(text);
  }

  if (paragraphs.length === 0 && polished.length > 20) {
    if (!isGematriaOrMetaLine(polished)) paragraphs.push(polished);
  }

  return paragraphs;
}

export type ReadingPackSectionV1 = {
  title: string;
  excerpt: string;
};

/** Parse ### Pack headings from reading-pack markdown (display only). */
export function parseReadingPackSections(readingPack: string): ReadingPackSectionV1[] {
  const raw = (readingPack || "").trim();
  if (!raw) return [];

  const introSplit = /^([\s\S]*?)(?=\n###\s+)/.exec(raw);
  const sectionSource = introSplit ? raw.slice(introSplit[0].length).trim() : raw;
  const chunks = sectionSource.split(/\n(?=###\s+)/).map((c) => c.trim()).filter(Boolean);
  const sections: ReadingPackSectionV1[] = [];

  for (const chunk of chunks) {
    const m = /^###\s*(.+?)(?:\n|$)/.exec(chunk);
    if (!m) continue;
    const title = stripMarkdownInline(m[1]);
    const body = chunk.slice(m[0].length).trim();
    const excerpt = body
      .split(/\n+/)
      .map((line) => stripMarkdownInline(line))
      .filter((line) => line.length > 8 && !isGematriaOrMetaLine(line))
      .join(" ")
      .trim();
    if (title || excerpt) {
      sections.push({ title: title || "읽기 프레임", excerpt });
    }
  }

  if (!sections.length && raw.length > 20) {
    sections.push({ title: "읽기 프레임", excerpt: stripMarkdownInline(raw).slice(0, 900) });
  }

  return sections;
}

export function readingPackIntroLine(readingPack: string): string {
  const raw = (readingPack || "").trim();
  if (!raw) return "";
  const introSplit = /^([\s\S]*?)(?=\n###\s+)/.exec(raw);
  const intro = (introSplit?.[1] ?? raw.split(/\n###\s+/)[0] ?? "").trim();
  return stripMarkdownInline(intro).slice(0, 220);
}

export type PublicInquiryDisplayModelV1 = {
  narrativeParagraphs: string[];
  readingPackSections: ReadingPackSectionV1[];
  readingPackIntro: string;
  publicCharCount: number;
};

export type CitationPathLabelV1 = "hub_preset" | "dynamic_graphrag" | "unknown";

export type PublicCitationLockModelV1 = {
  verseRefs: string[];
  anchorCount: number;
  pathLabel: CitationPathLabelV1;
  presetId: string | null;
  hubId: string | null;
  previewAnchors: string[];
};

/** Parse `inquiry_golden_hub_{hub_id}` token from query_mode (display only). */
export function extractGoldenHubIdFromQueryMode(queryMode?: string | null): string | null {
  const qm = String(queryMode ?? "");
  const m = /inquiry_golden_hub_([a-z0-9_]+)/i.exec(qm);
  return m?.[1] ?? null;
}

export function citationPathLabelKo(label: CitationPathLabelV1): string {
  if (label === "hub_preset") return "Hub preset 경로";
  if (label === "dynamic_graphrag") return "동적 GraphRAG 경로";
  return "경로 확인 중";
}

/** Public Ask UI — no engineering tags (Hub preset / GraphRAG). */
export function citationPathLabelPublicKo(label: CitationPathLabelV1): string {
  if (label === "hub_preset") return "주제 경로";
  if (label === "dynamic_graphrag") return "탐색 경로";
  return "경로 확인 중";
}

/** 1-hop display reason for “why this verse” (path provenance only; not doctrine). */
export function citationWhyVerseOneHopKo(model: PublicCitationLockModelV1): string {
  const lead = model.verseRefs[0];
  if (!lead) return "";
  if (model.pathLabel === "hub_preset") {
    return `${lead} — 질문과 맞는 주제 경로의 첫 앵커입니다 (연구 참고).`;
  }
  if (model.pathLabel === "dynamic_graphrag") {
    return `${lead} — 질문에서 1홉으로 이어진 근거 구절입니다 (연구 참고).`;
  }
  return `${lead} — 리포트 상단 출처 고정 앵커입니다 (연구 참고).`;
}

/** Public Trust UI — S1 citation lock (display only; API unchanged). */
export function buildPublicCitationLockModel(
  report?: Pick<LogosInquiryReportV1, "preset_id" | "query_mode" | "sections" | "query"> | null,
  snapshot?: StreamSnapshot | null,
): PublicCitationLockModelV1 | null {
  const s1 = report?.sections?.S1 ?? snapshot?.S1;
  if (!s1) return null;
  let verseRefs = [...(s1.verse_refs ?? [])].slice(0, 8);
  const query = report?.query ?? "";
  if (detectPsalm23Topic(query)) {
    const ps23 = verseRefs.filter((r) => /^Ps\.23/i.test(String(r).replace(/\s/g, "")));
    const rest = verseRefs.filter((r) => !/^Ps\.23/i.test(String(r).replace(/\s/g, "")));
    verseRefs = ps23.length ? [...ps23, ...rest] : verseRefs;
  }
  const anchors = s1.citation_lock_anchors ?? [];
  if (!verseRefs.length && !anchors.length) return null;

  const presetId = report?.preset_id ?? null;
  const qm = report?.query_mode ?? "";
  const hubId = extractGoldenHubIdFromQueryMode(qm);
  let pathLabel: CitationPathLabelV1 = "unknown";
  if (hubId || presetId) {
    pathLabel = "hub_preset";
  } else if (qm.toLowerCase().includes("graphrag") || qm.toLowerCase().includes("dynamic") || qm.toLowerCase().includes("longtail")) {
    pathLabel = "dynamic_graphrag";
  } else if (verseRefs.length) {
    pathLabel = "dynamic_graphrag";
  }

  return {
    verseRefs,
    anchorCount: anchors.length,
    pathLabel,
    presetId,
    hubId,
    previewAnchors: anchors.slice(0, 3),
  };
}

export function citationLockVerseTitle(ref: string): string {
  return `고정 구절 · ${ref}`;
}

/** Ring 0 must not expose engineering/system tags to general readers. */
export const PUBLIC_RING0_FORBIDDEN_RE =
  /\[NON_GATING\]|\[HYPO\]|Hub preset|Golden hub|citation lock anchors?:|\banchor\s*\d+\s*건|research_only|send_gate/i;

export function meetsPublicRing0Cleanliness(text: string): boolean {
  return !PUBLIC_RING0_FORBIDDEN_RE.test(text || "");
}

const PIPELINE_QUERY_SUFFIX_RE =
  /\s*—\s*학파별 해석 차이·(?:citation\s*lock|본문\s*앵커)·lemma 네트워크 관점에서 연구 요약해 달라\s*/gi;

export function healAskDisplayOrphanPunctV1(text: string): string {
  return (text || "")
    .replace(/\s*[—–-]\s*[.!?。！？]/g, ".")
    .replace(/·\s*[.!?。！？]/g, ".")
    .replace(/([가-힣A-Za-z0-9」』"'”’)\]])\s+([.!?。！？])/g, "$1$2")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/** Remove intake enrich echo and duplicated query prefix from public S4 (display only). */
export function stripPipelineQueryEcho(text: string, displayQuery?: string): string {
  let t = (text || "").trim();
  t = t.replace(/^질문:\s*/i, "");
  t = t.replace(PIPELINE_QUERY_SUFFIX_RE, " ").trim();
  if (displayQuery) {
    const dq = displayQuery.trim().replace(/^["'「『]+|["'」』]+$/g, "");
    if (dq) {
      const esc = dq.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const quotedSubjectLead = new RegExp(`^[「『"'“‘]\\s*${esc}\\s*[」』"'”’]`);
      if (!quotedSubjectLead.test(t) && t.startsWith(dq)) {
        t = t.slice(dq.length).replace(/^[—–-]\s*/, "").trim();
      }
    }
  }
  t = t.replace(/^」\s*(?:에\s*대한|은\(는\)|은|는)?\s*/u, "").trim();
  return t.replace(/\s{2,}/g, " ").trim();
}

export function isVerseOnlyBulletLine(line: string): boolean {
  const t = stripMarkdownInline(line).replace(/^[-*•]\s+/, "").trim();
  if (!t || t.length > 80) return false;
  if (/[가-힣]{5,}/.test(t)) return false;
  return /^(?:[1-3]\s*)?[A-Za-z]+\.\d+(?:\.\d+)?(?:\s*[·,]\s*[A-Za-z]+\.\d+(?:\.\d+)?)*$/.test(t);
}

/** Collapse `- Ps.23.1` bullet runs into one prose sentence (display only). */
export function collapseVerseBulletsToProse(text: string): string {
  const lines = (text || "").split(/\n+/).map((l) => l.trim()).filter(Boolean);
  const prose: string[] = [];
  const verseRefs: string[] = [];

  const flushVerses = () => {
    if (!verseRefs.length) return;
    prose.push(`본문 근거 구절로 ${verseRefs.join(" · ")}을 둡니다.`);
    verseRefs.length = 0;
  };

  for (const line of lines) {
    if (isVerseOnlyBulletLine(line)) {
      const ref = stripMarkdownInline(line).replace(/^[-*•]\s+/, "").trim();
      if (ref && !verseRefs.includes(ref)) verseRefs.push(ref);
      continue;
    }
    flushVerses();
    const cleaned = stripMarkdownInline(line);
    if (cleaned.length > 8 && !isGematriaOrMetaLine(cleaned)) prose.push(cleaned);
  }
  flushVerses();
  return prose.join("\n\n");
}

export function polishPublicS4SectionBody(body: string, displayQuery?: string): string {
  const stripped = stripPipelineQueryEcho(stripPublicResearchTags(body), displayQuery);
  const collapsed = collapseVerseBulletsToProse(stripped);
  return collapsed.replace(/\n{3,}/g, "\n\n").trim();
}

const INQUIRY_S4_SECTION_HEADERS = [
  "### 핵심 주장",
  "### 근거 구절",
  "### 반증·대안",
  "### 한계·주의",
  "### 다음 행동 제안",
] as const;

/** M-β — section-aware essay polish for inquiry report S4 (azure or deterministic gate output). */
export function polishInquiryS4EssayBodyMbeta(body: string, displayQuery?: string): string {
  const raw = (body || "").trim();
  if (!raw) return raw;
  const packSplit = raw.split(/\n---\n/);
  const mainRaw = packSplit[0]?.trim() ?? raw;
  const appendix = packSplit.length > 1 ? packSplit.slice(1).join("\n---\n").trim() : "";

  const hasAll = INQUIRY_S4_SECTION_HEADERS.every((h) => mainRaw.includes(h));
  if (!hasAll) {
    const polished = polishPublicS4SectionBody(mainRaw, displayQuery);
    return appendix ? `${polished}\n\n---\n\n${appendix}` : polished;
  }

  const parts: string[] = [];
  for (let i = 0; i < INQUIRY_S4_SECTION_HEADERS.length; i += 1) {
    const header = INQUIRY_S4_SECTION_HEADERS[i];
    const escaped = header.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const nextHeader = INQUIRY_S4_SECTION_HEADERS[i + 1];
    const nextEscaped = nextHeader ? nextHeader.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") : null;
    const sectionRe = nextEscaped
      ? new RegExp(`${escaped}\\s*\\n([\\s\\S]*?)(?=\\n${nextEscaped}\\s*(?:\\n|$))`)
      : new RegExp(`${escaped}\\s*\\n([\\s\\S]*)$`);
    const sectionMatch = sectionRe.exec(mainRaw);
    const sectionBody = (sectionMatch?.[1] ?? "").trim();
    parts.push(header, polishPublicS4SectionBody(sectionBody, displayQuery), "");
  }
  const main = parts.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  return appendix ? `${main}\n\n---\n\n${appendix}` : main;
}

export function buildPublicInquiryDisplayModel(s4Body: string, displayQuery?: string): PublicInquiryDisplayModelV1 {
  const { narrative, readingPack } = splitS4PublicBody(s4Body);
  const narrativeParagraphs = formatPublicNarrativeParagraphs(s4Body, displayQuery);
  const readingPackSections = parseReadingPackSections(readingPack);
  const readingPackIntro = readingPackIntroLine(readingPack);
  const publicText = [...narrativeParagraphs, readingPackIntro].join("\n");
  return {
    narrativeParagraphs,
    readingPackSections,
    readingPackIntro,
    publicCharCount: publicText.length,
  };
}

/** Aligns with live battery narrative_ok heuristic (display layer). */
export function meetsPublicNarrativeQuality(
  s4Body: string,
  opts: { minChars?: number; minParagraphs?: number; displayQuery?: string } = {},
): { narrative_ok: boolean; char_count: number; paragraph_count: number; verse_bullet_spam: boolean } {
  const minChars = opts.minChars ?? 120;
  const minParagraphs = opts.minParagraphs ?? 2;
  const model = buildPublicInquiryDisplayModel(s4Body, opts.displayQuery);
  const char_count = model.publicCharCount;
  const paragraph_count = model.narrativeParagraphs.length;
  const verse_bullet_spam = /^[-*•]\s+[A-Za-z]+\.\d/m.test(
    model.narrativeParagraphs.join("\n"),
  );
  return {
    narrative_ok:
      char_count >= minChars && paragraph_count >= minParagraphs && !verse_bullet_spam,
    char_count,
    paragraph_count,
    verse_bullet_spam,
  };
}

export const PUBLIC_INQUIRY_DISCLAIMER_KO =
  "성경·신학 연구 참고 자료입니다. 종교·의료·투자 확정이 아닙니다.";

export function isDevMetadataExpandedDefault(): boolean {
  const raw = (process.env.NEXT_PUBLIC_LOGOS_INQUIRY_DEV_METADATA || "collapsed").trim().toLowerCase();
  return raw === "open" || raw === "1" || raw === "true";
}

/** Phase-A teaser lines (S1–S3 snapshot) before S4 stream body arrives. */
export function snapshotExecutiveLines(snapshot: StreamSnapshot, maxLines = 3): string[] {
  const lines: string[] = [];
  const refs = snapshot.S1?.verse_refs ?? [];
  if (refs.length) {
    const preview = refs.slice(0, 3).join(" · ");
    lines.push(`S1 citation lock — ${refs.length} refs (${preview})`);
  }
  const s2 = snapshot.S2;
  if (s2) {
    const count = s2.lemma_edge_line_count ?? "—";
    lines.push(`S2 lexicon pin — ${count} / floor ${s2.min_line_count_floor}`);
  }
  const groups = snapshot.S3?.groups ?? [];
  if (groups.length) {
    lines.push(`S3 divergence — ${groups.length} group(s) · [NON_GATING]`);
  } else if (snapshot.S3?.note_ko) {
    lines.push(`S3 — ${snapshot.S3.note_ko.slice(0, 72)}`);
  }
  return lines.slice(0, maxLines);
}

export function snapshotExecutiveText(snapshot: StreamSnapshot, maxLines = 3): string {
  return snapshotExecutiveLines(snapshot, maxLines).join("\n");
}

/** Opaque Gematria_Pin preview — no numerology values or coordinate map. */
export function gematriaPinAuxLine(s2: InquiryAuxS2): string | null {
  const pins = (s2?.path_token_preview ?? []).filter((t) => /^Gematria_Pin:/i.test(String(t).trim()));
  if (!pins.length) return null;
  const preview = pins
    .slice(0, 2)
    .map((p) => {
      const v = String(p).trim();
      return v.length > 24 ? `${v.slice(0, 22)}…` : v;
    })
    .join(" · ");
  const extra = pins.length > 2 ? ` (+${pins.length - 2})` : "";
  return `게마트리아 핀 ${pins.length}건 — ${preview}${extra} · 수치·좌표맵 비공개`;
}

/** B-track sasang regime hint — [HYPO][NON_GATING] display only. */
export function sasangHintAuxLine(s3: InquiryAuxS3): string | null {
  const hint = s3?.regime_hint_b_track as SasangRegimeHintBTrack | null | undefined;
  if (!hint) return null;
  const parts: string[] = [];
  if (hint.regime_hypothesis?.trim()) parts.push(hint.regime_hypothesis.trim());
  if (hint.mapping_target?.trim()) parts.push(`→ ${hint.mapping_target.trim()}`);
  const core = parts.length ? parts.join(" ") : hint.token?.trim() || "사상 토큰";
  return `[HYPO][NON_GATING] 사상 B-track — ${core}`;
}

export function researchAuxInsightLines(s2: InquiryAuxS2, s3: InquiryAuxS3): string[] {
  const lines: string[] = [];
  const gem = gematriaPinAuxLine(s2);
  const sas = sasangHintAuxLine(s3);
  if (gem) lines.push(gem);
  if (sas) lines.push(sas);
  return lines;
}

export function isPlaceholderAssistantTurn(turn: {
  role: string;
  text?: string;
  error?: string;
  report?: unknown;
  textMvpReport?: unknown;
  snapshot?: unknown;
  streamingS4?: string;
  streamPhase?: string;
}): boolean {
  if (turn.role !== "assistant" || turn.error) return false;
  if (turn.report || turn.textMvpReport || turn.snapshot || turn.streamingS4) return false;
  if (turn.streamPhase && turn.streamPhase !== "done") return false;
  const text = (turn.text || "").trim();
  return text === "" || text === "…";
}

export type PublicSchoolGroupV1 = {
  conflict_group_id?: string;
  lexicon_base?: string;
  school_count?: number;
  schools?: Array<{
    school_tier?: string;
    interpretation_ko?: string;
    verse_refs?: string[];
    traditions?: string[];
  }>;
};

export function countPublicSchoolRows(groups: PublicSchoolGroupV1[] | null | undefined): number {
  let n = 0;
  for (const group of groups ?? []) {
    n += group.schools?.length ?? 0;
  }
  return n;
}

export { detectSchoolComparisonIntent } from "./logosInquiryTopicDetectV1";

export function shouldShowPublicSchoolCards(
  query: string,
  groups: PublicSchoolGroupV1[] | null | undefined,
): boolean {
  const schoolCount = countPublicSchoolRows(groups);
  if (schoolCount < 1) return false;
  return detectSchoolComparisonIntent(query) || detectPsalm23Topic(query) || schoolCount >= 2;
}

/** Done-Product ceiling — complements harness smokes (display/rubric only). */
export function meetsDoneProductGoldenRubric(input: {
  query: string;
  s4Body: string;
  verseRefs?: string[];
  schoolGroups?: PublicSchoolGroupV1[] | null;
}): {
  product_ok: boolean;
  stub_free: boolean;
  psalm23_anchor_ok: boolean;
  school_cards_ok: boolean;
  ring0_clean: boolean;
} {
  const { narrative } = splitS4PublicBody(input.s4Body);
  const stub_free = !PUBLIC_S4_STUB_PHRASE_RE.test(narrative || input.s4Body);
  const psalm23 = detectPsalm23Topic(input.query);
  const refs = (input.verseRefs ?? []).map((r) => String(r));
  const psalm23_anchor_ok = !psalm23 || refs.some((r) => /^Ps\.23/i.test(r.replace(/\s/g, "")));
  const school_cards_ok =
    !detectSchoolComparisonIntent(input.query) && !psalm23
      ? true
      : countPublicSchoolRows(input.schoolGroups) >= 2 ||
        (psalm23 && countPublicSchoolRows(input.schoolGroups) >= 1);
  const narrativeQuality = meetsPublicNarrativeQuality(input.s4Body, { displayQuery: input.query });
  const ring0_clean = meetsPublicRing0Cleanliness(
    [polishPublicS4SectionBody(input.s4Body, input.query), PUBLIC_INQUIRY_DISCLAIMER_KO].join("\n"),
  );
  const product_ok =
    stub_free &&
    narrativeQuality.narrative_ok &&
    psalm23_anchor_ok &&
    school_cards_ok &&
    ring0_clean;
  return { product_ok, stub_free, psalm23_anchor_ok, school_cards_ok, ring0_clean };
}

/** Scholar-mode chip — intent_compress enrich only (NOT Track A KPI). */
export function formatIntentCompressChipKo(
  intent:
    | {
        intent_core?: string;
        topic_id?: string;
      }
    | null
    | undefined,
): string | null {
  if (!intent) return null;
  const core = String(intent.intent_core ?? "").trim();
  if (!core || core === "(empty)") return null;
  if (intent.topic_id === "ai_society_symbolism") {
    return "AI·형상·우상 상징 읽기 [HYPO]";
  }
  const oneLine = core.replace(/\s+/g, " ");
  return oneLine.length > 72 ? `${oneLine.slice(0, 69)}…` : oneLine;
}

const LOGOS_ASK_ERROR_KO: Record<string, string> = {
  preset_not_matched:
    "등록된 성경 앵커에 확실히 연결되지 않았습니다. 권·장·구절을 포함해 구체화해 주세요.",
  preset_missing:
    "해당 질문을 바로 연결할 연구 팩이 없습니다. 구절·주제를 조금 더 구체적으로 적어 주세요.",
  quota_exceeded:
    "오늘 무료 질문 한도를 모두 사용했습니다. UTC 자정 이후 다시 시도해 주세요.",
  query_failed: "질문 처리에 실패했습니다. 잠시 후 다시 시도해 주세요.",
  rate_limited: "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.",
  unauthorized: "인증이 필요합니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.",
};

/**
 * Friend-floor Ask errors: prefer Korean hint / reverse Q over raw machine codes.
 */
export function formatLogosAskError(
  error?: string | null,
  hint?: string | null,
  reverseQuestionsKo?: string[] | null,
): string {
  const rev = (reverseQuestionsKo ?? []).map((q) => String(q || "").trim()).filter(Boolean);
  if (rev.length) return rev[0];

  const hintTrim = String(hint ?? "").trim();
  const errTrim = String(error ?? "").trim();

  // Prefer explicit Korean/human hint when present and not a bare snake_case code.
  if (hintTrim && !/^[a-z][a-z0-9_]*$/i.test(hintTrim)) {
    return hintTrim;
  }
  if (hintTrim && hintTrim !== errTrim) {
    return hintTrim;
  }

  if (errTrim && LOGOS_ASK_ERROR_KO[errTrim]) {
    return LOGOS_ASK_ERROR_KO[errTrim];
  }
  // Already human text (e.g. stream onError with hint as message)
  if (errTrim && !/^[a-z][a-z0-9_]*$/i.test(errTrim)) {
    return errTrim;
  }
  if (errTrim) {
    return LOGOS_ASK_ERROR_KO.preset_not_matched;
  }
  return LOGOS_ASK_ERROR_KO.query_failed;
}