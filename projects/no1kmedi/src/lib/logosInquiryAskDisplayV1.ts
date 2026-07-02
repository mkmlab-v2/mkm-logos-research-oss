/** Commander-facing ask UI — 3-line executive summary (display only, not API schema). */
import type { LogosInquiryReportV1 } from "./logosInquiryReportV1";
import type { StreamSnapshot } from "./logosInquiryStreamV1";
import type { SasangRegimeHintBTrack } from "./logosInquiryFreezeMetaV1";
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
  /combined_sum|vector_4d|hub_score|state16|Gematria_Pin|topology pin|mispar_|lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절|^\*\*(Query|Pack|Governance|query_id|utterance_class):/i;

export function isGematriaOrMetaLine(line: string): boolean {
  const t = (line || "").trim();
  if (!t) return true;
  return GEMATRIA_OR_META_LINE_RE.test(t) || isStudioBoilerplateKo(t);
}

export type S4PublicSectionV1 = {
  title: string;
  body: string;
};

/** Public S4 — preserve ### section structure for Ask UI (display only). */
export function parseS4PublicSections(body: string): S4PublicSectionV1[] {
  const { narrative } = splitS4PublicBody(body);
  const source = narrative || stripPublicResearchTags(body);
  if (!source) return [];

  const chunks = source.split(/\n(?=###\s+)/).map((c) => c.trim()).filter(Boolean);
  const sections: S4PublicSectionV1[] = [];

  for (const chunk of chunks) {
    const heading = /^###\s*(.+?)(?:\n|$)/.exec(chunk);
    if (!heading) {
      const flat = chunk
        .replace(/\n+/g, " ")
        .replace(/\s{2,}/g, " ")
        .trim();
      if (flat.length > 20 && !isGematriaOrMetaLine(flat)) {
        sections.push({ title: "통찰", body: flat });
      }
      continue;
    }
    const title = stripMarkdownInline(heading[1]);
    const bodyText = chunk
      .slice(heading[0].length)
      .trim()
      .split(/\n+/)
      .map((line) => stripMarkdownInline(line))
      .filter((line) => line.length > 0 && !isGematriaOrMetaLine(line))
      .join("\n\n");
    if (title || bodyText) {
      sections.push({ title: title || "통찰", body: bodyText });
    }
  }

  if (sections.length) return sections;

  const paragraphs = formatPublicNarrativeParagraphs(body);
  return paragraphs.map((p, i) => ({
    title: i === 0 ? "통찰" : `통찰 ${i + 1}`,
    body: p,
  }));
}

/** Public narrative — paragraph blocks for primary insight UI (display only). */
export function formatPublicNarrativeParagraphs(body: string): string[] {
  const { narrative } = splitS4PublicBody(body);
  const source = narrative || stripPublicResearchTags(body);
  if (!source) return [];

  const blocks = source.split(/\n{2,}|\n(?=###\s+)/).map((p) => p.trim()).filter(Boolean);
  const paragraphs: string[] = [];

  for (const block of blocks) {
    if (isGematriaOrMetaLine(block)) continue;
    let text = block;
    if (text.startsWith("###")) {
      const lines = text.split(/\n+/).map((l) => l.trim()).filter(Boolean);
      const title = lines[0]?.replace(/^###\s*\d*\.?\s*/, "").trim() ?? "";
      const body = lines.slice(1).join(" ").trim();
      text = [title, body].filter(Boolean).join(" — ");
    } else {
      text = text.replace(/\n+/g, " ").replace(/\s{2,}/g, " ").trim();
    }
    if (text.length > 20 && !isGematriaOrMetaLine(text)) paragraphs.push(text);
  }

  if (paragraphs.length === 0 && source.length > 20) {
    const single = source.replace(/\n+/g, " ").replace(/\s{2,}/g, " ").trim();
    if (!isGematriaOrMetaLine(single)) paragraphs.push(single);
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

/** Public Trust UI — S1 citation lock (display only; API unchanged). */
export function buildPublicCitationLockModel(
  report?: Pick<LogosInquiryReportV1, "preset_id" | "query_mode" | "sections"> | null,
  snapshot?: StreamSnapshot | null,
): PublicCitationLockModelV1 | null {
  const s1 = report?.sections?.S1 ?? snapshot?.S1;
  if (!s1) return null;
  const verseRefs = [...(s1.verse_refs ?? [])].slice(0, 8);
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
  return `Citation lock · ${ref} · S1 고정 · [NON_GATING]`;
}

export function buildPublicInquiryDisplayModel(s4Body: string): PublicInquiryDisplayModelV1 {
  const { narrative, readingPack } = splitS4PublicBody(s4Body);
  const narrativeParagraphs = formatPublicNarrativeParagraphs(s4Body);
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
  opts: { minChars?: number; minParagraphs?: number } = {},
): { narrative_ok: boolean; char_count: number; paragraph_count: number } {
  const minChars = opts.minChars ?? 120;
  const minParagraphs = opts.minParagraphs ?? 2;
  const model = buildPublicInquiryDisplayModel(s4Body);
  const char_count = model.publicCharCount;
  const paragraph_count = model.narrativeParagraphs.length;
  return {
    narrative_ok: char_count >= minChars && paragraph_count >= minParagraphs,
    char_count,
    paragraph_count,
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
