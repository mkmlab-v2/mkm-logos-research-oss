/**
 * User-facing Ask answer hygiene — commander bar + pipeline-jargon scrub.
 * Internal meta stays in debug / data-* only; never Ring-0 body prose.
 */

import { isStudioBoilerplateKo } from "./logosStudioBoilerplateV1";
import { stripPublicS4OpsJargon } from "./logosInquiryPublicS4FilterV1";
import { rewriteOsisRefsInProseToKoV1 } from "./logosAskVerseLabelKoV1";
import { dedupeVerseRefsInProse } from "./logosAskAnswerShapeGateV1";
import {
  healAskDisplayOrphanPunctV1,
  stripPipelineQueryEcho,
} from "./logosInquiryAskDisplayV1";

/** Commander lock: 짧은 답 → 신뢰 등급 → 근거 본문 → 해석 갈래 → 한계 */
export const COMMANDER_ANSWER_SECTION_TITLES = [
  "### 짧은 답",
  "### 신뢰 등급",
  "### 근거 본문",
  "### 해석 갈래",
  "### 한계",
] as const;

export const PIPELINE_JARGON_BODY_RE =
  /query-time|conflict\s*join|deterministic\s*synthesis|G3\s*hypo|idea\s*card|TSK\s*전량|open\s*LLM|citation\s*lock|\[NON_GATING\]|send_gate|product_all_ok|Done-?Harness|trust_face|LLM-OFF|RUNTIME-OFF|LLM-ON|RUNTIME-ON|research_only|GraphRAG|path\s*envelope|lemma\s*bridge|why_question_assembled|:hebrew:|gematria\s*합선/i;

/** Friend/pastor surface — no bare HOLD jargon (machine send_gate stays elsewhere). */
export const LOGOS_ASK_FRIEND_HOLD_LINE_KO =
  "연구 범위 안내 · 자동 설교·전송 아님" as const;

export function publicAskHoldLineKo(raw: string | null | undefined): string {
  const t = String(raw || "").trim();
  if (!t) return LOGOS_ASK_FRIEND_HOLD_LINE_KO;
  if (/HOLD|전송\s*보류|send_gate/i.test(t)) return LOGOS_ASK_FRIEND_HOLD_LINE_KO;
  return scrubPipelineJargonFromUserBody(t) || LOGOS_ASK_FRIEND_HOLD_LINE_KO;
}

const DEV_PATH_NOTE_RE =
  /G3\s*hypo|topical\s*freeform|offtopic\s*redirect|confidence_gate|GraphRAG\s*bypass|\[HYPO\]|\[NON_GATING\]|synthesis|query-time/i;

const SCHOOL_TIER_KO: Record<string, string> = {
  "1": "전통 A",
  "2": "전통 B",
  "3": "전통 C",
  a: "제2성전기·외경 축",
  b: "역사·문법·교부 축",
  c: "문헌·비평 축",
  major: "주류 독법",
  historical: "역사·문법",
  literary: "문학·지혜",
  theological: "신학",
  allegorical: "비유·상징",
  primary: "주요 독법",
  high: "고강도 주장",
  middle: "중간 축",
  low: "약한 축",
  tier_2: "2차 축",
  "tier 2": "2차 축",
  retribution: "응보 독법",
  theodicy_mystery: "신정론·신비",
  theodicy: "신정론",
  "divine speech": "여호와의 응답",
  "friends dialogue": "친구들 대화",
  "wisdom dialogue": "지혜 대화",
  "retribution theology": "응보 신학",
};

export function scrubPipelineJargonFromUserBody(text: string): string {
  let t = String(text || "");
  t = t
    // Backtick-wrapped tags first — else scrub leaves empty `` → 「연구 참고(``)」.
    .replace(/`\s*\[(?:HYPO|NON_GATING)\](?:\s*\[(?:HYPO|NON_GATING)\])*\s*`/gi, "")
    .replace(/\[HYPO\]\s*/gi, "")
    .replace(/\[NON_GATING\]\s*/gi, "")
    .replace(/^(?:\*\*)?(?:Query|Pack|Governance|query_id|utterance_class)\s*:.*$/gim, "")
    .replace(/\bquery_id\s*:\s*\S+/gi, "")
    .replace(/\butterance_class\s*:\s*\S+/gi, "")
    .replace(/\bintegrated_topology\b/gi, "")
    .replace(/\bscope_reset_no_why\b/gi, "")
    .replace(/\bliteral_council_only\b/gi, "")
    .replace(/5노드\s*변이[^\n]*/gi, "")
    .replace(/theme_39[^\n]*/gi, "")
    .replace(/\[HYPO\s*ops\]/gi, "")
    .replace(/why_question_assembled\s*=\s*(?:true|false)/gi, "")
    .replace(/\(\s*why_question_assembled\s*=\s*(?:true|false)\s*\)/gi, "")
    .replace(/via\s*·\s*:hebrew:[^\s)\]|,]*/gi, "")
    .replace(/:hebrew:[A-Za-z0-9_.:-]+/gi, "")
    .replace(/gematria\s*합선\s*없음\.?/gi, "")
    .replace(/전송\s*보류\s*\(?\s*HOLD\s*\)?/gi, "연구 참고")
    .replace(/query-time\s*conflict\s*join\s*\+\s*deterministic\s*synthesis\s*—?\s*/gi, "")
    .replace(/TSK\s*전량[·\s]*open\s*LLM\s*합성\s*아님\.?/gi, "")
    .replace(/TSK\s*전량/gi, "")
    .replace(/open\s*LLM\s*합성\s*아님\.?/gi, "")
    .replace(/deterministic\s*synthesis/gi, "")
    .replace(/conflict\s*join/gi, "")
    .replace(/query-time/gi, "")
    .replace(/G3\s*hypo\s*idea\s*card/gi, "가설·상상 카드")
    .replace(/가설·상상\s*idea\s*card/gi, "가설·상상 카드")
    .replace(/G3\s*hypo/gi, "")
    .replace(/idea\s*card/gi, "가설·상상 카드")
    .replace(/Done-?Harness/gi, "")
    .replace(/\btrust_face(?:_ko)?\b/gi, "")
    .replace(/\bLLM-OFF\b/gi, "")
    .replace(/\bRUNTIME-OFF\b/gi, "")
    .replace(/\bLLM-ON\b/gi, "")
    .replace(/\bRUNTIME-ON\b/gi, "")
    .replace(/send_gate\s*:\s*\w+/gi, "")
    .replace(/product_all_ok\s*=?\s*\w*/gi, "")
    .replace(/\bresearch_only\b/gi, "")
    .replace(/citation[- ]?lock/gi, "본문 앵커")
    .replace(/실매매/gi, "");
  t = stripPublicS4OpsJargon(t);
  // Public Ask: drop markdown section hashes (keep title text).
  t = t.replace(/(?:^|\n)\s*#{1,6}\s+/gm, "\n").replace(/#{1,6}/g, "");
  t = scrubEllipsisTruncationArtifacts(t);
  // KO UI: answer body should match evidence-panel Korean refs (not bare Heb.11.1).
  t = rewriteOsisRefsInProseToKoV1(t);
  // After OSIS→KO, drop duplicate verse labels that leave hanging particles (은/는/의…).
  t = dedupeVerseRefsInProse(t, 3);
  t = t
    .replace(/`\s*`/g, "")
    // Empty corner-quotes after OSIS/Latin scrub (「」 / 「 」) — never leave bare brackets.
    .replace(/「\s*」/g, "")
    .replace(/「\s*([^」]*?)\s*」/g, (_m, inner: string) => {
      const core = String(inner || "").trim();
      if (!core || !/[가-힣A-Za-z0-9]/.test(core)) return "";
      return `「${core}」`;
    })
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/·\s*·/g, "·")
    .replace(/\(\s*\)/g, "")
    .replace(/연구\s*참고\s*\(\s*\)/g, "연구 참고")
    .trim();
  // Studio path: citation lock → 본문 앵커 runs here before Ask polish — strip both forms.
  t = stripPipelineQueryEcho(t);
  return healAskDisplayOrphanPunctV1(t);
}

/**
 * B5: drop EN-heavy mid-cut lines ending in … / ...; terminate KO lines without ellipsis clip.
 */
export function scrubEllipsisTruncationArtifacts(text: string): string {
  const lines = String(text || "").split("\n");
  const out: string[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      out.push(line);
      continue;
    }
    const bullet = trimmed.match(/^([-*•]\s*)([\s\S]*)$/);
    const prefix = bullet ? bullet[1] : "";
    const core = bullet ? bullet[2] : trimmed;
    if (core.length >= 40 && /(?:\.\.\.|…)\s*$/u.test(core)) {
      const latin = (core.match(/[A-Za-z]/g) || []).length;
      const hangul = (core.match(/[가-힣]/g) || []).length;
      if (latin >= 24 && hangul < 8) {
        // Drop EN dump clipped with ellipsis (e.g. "as elaborated in biblical and…")
        continue;
      }
      const cleaned = core.replace(/(?:\.\.\.|…)\s*$/u, "").trim();
      if (cleaned) out.push(`${prefix}${/[.!?。！？]$/u.test(cleaned) ? cleaned : `${cleaned}.`}`);
      continue;
    }
    // Inline EN fragment ending with ellipsis mid-line
    if (/[A-Za-z]{12,}[^가-힣]{0,80}(?:\.\.\.|…)/u.test(core) && hangulLen(core) < 8) {
      const latin = (core.match(/[A-Za-z]/g) || []).length;
      if (latin >= 24) continue;
    }
    out.push(line);
  }
  return out.join("\n");
}

export function isPipelineJargonUserBody(text: string): boolean {
  const t = (text || "").trim();
  if (!t) return true;
  if (PIPELINE_JARGON_BODY_RE.test(t)) return true;
  if (isStudioBoilerplateKo(t)) return true;
  return false;
}

export function isDeveloperPathNoteKo(note: string): boolean {
  const t = (note || "").trim();
  if (!t) return true;
  return DEV_PATH_NOTE_RE.test(t) || isPipelineJargonUserBody(t);
}

const SCHOOL_EN_ONLY_FALLBACK_KO =
  "이 축은 영어 원문 요약을 한국어로 압축한 참고 독법입니다. 단일 교리·실행 지시가 아닙니다.";

function hangulLen(s: string): number {
  return (String(s || "").match(/[가-힣]/g) || []).length;
}

/** Prefer Korean segment before EN pipe dumps; drop field-label mash. */
export function formatSchoolInterpretationPublicKo(raw: string, maxLen = 280): string {
  const cleaned = scrubPipelineJargonFromUserBody(raw || "");
  if (!cleaned) {
    // EN dump / ellipsis scrub emptied body — KO fallback, never blank card on user path
    return String(raw || "").trim() ? SCHOOL_EN_ONLY_FALLBACK_KO : "";
  }
  const parts = cleaned
    .split(/\s*\|\s*/)
    .map((p) => p.trim())
    .filter(Boolean)
    .filter((p) => !/^(tier\s*\d+|high|middle|low|primary)$/i.test(p));
  const koFirst =
    parts.find((p) => /[가-힣]{8,}/.test(p)) ||
    parts.find((p) => /[가-힣]{2,}/.test(p)) ||
    "";
  if (koFirst) return truncatePublic(koFirst, maxLen);

  const enOnly = parts[0] || cleaned;
  // EN school dump-first — never ship raw EN paragraph / ellipsis clip on public cards
  const latin = (enOnly.match(/[A-Za-z]/g) || []).length;
  if (latin >= 18 && hangulLen(enOnly) < 8) {
    // Pure KO fallback only (no EN cue dump — gold/nephilim user path).
    return SCHOOL_EN_ONLY_FALLBACK_KO;
  }
  // Drop snake_case / keyword dumps
  if (/^[a-z0-9_,;\s-]{20,}$/i.test(enOnly) && !/[가-힣]/.test(enOnly)) {
    return SCHOOL_EN_ONLY_FALLBACK_KO;
  }
  // Mid-cut ellipsis leftovers (B5) — refuse rather than show truncated EN/KO mash
  if (/(?:\.\.\.|…)\s*$/u.test(enOnly) && hangulLen(enOnly) < 12) {
    return SCHOOL_EN_ONLY_FALLBACK_KO;
  }
  return truncatePublic(enOnly, maxLen);
}

export function mapSchoolTierLabelKo(tier: string | undefined | null): string {
  const raw = String(tier || "").trim();
  if (!raw) return "해석 축";
  const key = raw.toLowerCase();
  if (SCHOOL_TIER_KO[key]) return SCHOOL_TIER_KO[key];
  if (/^[ABC]$/i.test(raw)) return SCHOOL_TIER_KO[raw.toLowerCase()] || `해석 ${raw}`;
  if (/^\d+$/.test(raw)) return SCHOOL_TIER_KO[raw] || `해석 ${raw}`;
  if (/tier\s*2/i.test(raw)) return "2차 축";
  if (/^(high|middle|low|primary)$/i.test(raw)) {
    return SCHOOL_TIER_KO[raw.toLowerCase()] || "해석 축";
  }
  // Already human Korean
  if (/[가-힣]/.test(raw) && raw.length <= 24) return raw;
  return "해석 축";
}

/** Prefer complete sentence under maxLen — never mid-cut with … (B5 truncation gate). */
function truncatePublic(text: string, maxLen: number): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (t.length <= maxLen) return t;
  const slice = t.slice(0, maxLen);
  const sentence = slice.match(/^[\s\S]*[.!?。！？](?=\s|$)/u);
  if (sentence && sentence[0].trim().length >= 24) return sentence[0].trim();
  const sp = Math.max(slice.lastIndexOf(" "), slice.lastIndexOf("·"));
  const cut = (sp > 24 ? slice.slice(0, sp) : slice).trim();
  if (/[.!?。！？]$/u.test(cut)) return cut;
  // Complete without ellipsis — short KO period if mid-word cut.
  return /[가-힣]$/u.test(cut) ? `${cut}.` : `${cut}.`;
}

export function detectNephilimUfoDualTopic(query: string): boolean {
  const q = (query || "").trim();
  const nephilim = /네피림|nephilim|감시자|watcher|benei|하나님의\s*아들|sons\s*of\s*god|창세기\s*6|genesis\s*6/i.test(
    q,
  );
  const ufo = /UFO|유에프오|외계|외계인|비행체|미확인\s*비행|extraterrestrial|alien/i.test(q);
  return nephilim && ufo;
}

/** Ambiguous multi-topic (네피림 + UFO/외계) — force dual coverage in short block. */
export function composeAmbiguousMultiTopicShortAnswerKo(query: string): string {
  const q = (query || "").trim();
  const wantsAlien = /외계|alien|extraterrestrial/i.test(q);
  const wantsUfo = /UFO|유에프오|비행체|미확인\s*비행/i.test(q);
  const modernBits = [
    wantsUfo ? "UFO" : "",
    wantsAlien ? "외계인" : "",
  ]
    .filter(Boolean)
    .join("·");
  const modernLabel = modernBits || "UFO·외계";
  return [
    `네피림은 창세기 6장(‘하나님의 아들들’·거인 전승)을 중심으로 전통 해석이 갈립니다.`,
    `${modernLabel} 이야기는 같은 본문에 직접 나오지 않으며, 현대 가설·대중 독법으로 보는 편이 안전합니다.`,
    `둘을 하나의 본문 기록으로 묶거나 동일시하지 않습니다.`,
  ].join(" ");
}

export function hasCommanderAnswerSections(body: string): boolean {
  const t = body || "";
  return COMMANDER_ANSWER_SECTION_TITLES.every((title) => t.includes(title));
}

export function composeCommanderFiveBlockAnswerKo(input: {
  shortAnswerKo: string;
  trustFaceKo: string;
  evidenceKo: string;
  schoolsKo: string;
  limitsKo: string;
}): string {
  return [
    "### 짧은 답",
    scrubPipelineJargonFromUserBody(input.shortAnswerKo),
    "",
    "### 신뢰 등급",
    scrubPipelineJargonFromUserBody(input.trustFaceKo),
    "",
    "### 근거 본문",
    scrubPipelineJargonFromUserBody(input.evidenceKo),
    "",
    "### 해석 갈래",
    scrubPipelineJargonFromUserBody(input.schoolsKo),
    "",
    "### 한계",
    scrubPipelineJargonFromUserBody(input.limitsKo),
  ]
    .join("\n")
    .trim();
}

export function composeNephilimUfoCommanderAnswerKo(input: {
  trustFaceKo?: string;
  schoolBullets?: string[];
  verseLine?: string;
  query?: string;
}): string {
  const schools =
    (input.schoolBullets || []).filter(Boolean).slice(0, 5).join("\n") ||
    [
      "- 제2성전기·외경: 감시자·거인 후손 독법",
      "- 역사·문법: ‘하나님의 아들들’을 셋 계열·유력자 등으로 읽는 축",
      "- 현대 대중: UFO·외계와 연결하는 독법(본문 외 가설)",
    ].join("\n");
  const verse =
    input.verseLine?.trim() ||
    "창세기 6:1-4(네피림·하나님의 아들들)을 전통 논의의 출발점으로 둡니다. UFO·외계는 본문에 직접 등장하지 않습니다.";
  const shortAnswerKo = composeAmbiguousMultiTopicShortAnswerKo(
    input.query || "네피림 UFO 외계",
  );
  return composeCommanderFiveBlockAnswerKo({
    shortAnswerKo,
    trustFaceKo: input.trustFaceKo || "일반 참고 · 신뢰도 낮음",
    evidenceKo: verse,
    schoolsKo: schools,
    limitsKo:
      "연구 참고이며 교리·역사 사실·외계 존재 단정이 아닙니다. 학파·시대마다 읽기가 갈리며, UFO·외계 가설은 본문 밖 현대 해석층입니다. 전문 용어·파이프라인 라벨은 넣지 않습니다.",
  });
}

/** Canonical key for public verse dedupe (OSIS / Genesis 6:1-4 / 창세기). */
export function canonicalPublicVerseKey(raw: string): string {
  const t = String(raw || "")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/[),.;]+$/g, "");
  const m =
    t.match(/^(?:([1-3])\s*)?([A-Za-z가-힣]+)\.(\d{1,3})(?:\.(\d{1,3})(?:-(\d{1,3}))?)?$/i) ||
    t.match(/^(?:([1-3])\s*)?([A-Za-z가-힣]+)\s+(\d{1,3})(?::(\d{1,3})(?:-(\d{1,3}))?)?$/i);
  if (!m) return t.toLowerCase();
  const num = m[1] ? `${m[1]}` : "";
  const book = `${num}${m[2]}`.toLowerCase();
  const chap = m[3];
  const verse = m[4] || "";
  const end = m[5] || "";
  if (verse) return end ? `${book}.${chap}.${verse}-${end}` : `${book}.${chap}.${verse}`;
  return `${book}.${chap}`;
}

/** Filter garbage verse tokens (G3, 장 1, bare book names without chapter:verse). */
export function filterPublicVerseRefs(refs: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of refs || []) {
    const t = String(raw || "").trim();
    if (!t) continue;
    if (/^G\d+$/i.test(t)) continue;
    if (/^장\s*\d+$/i.test(t)) continue;
    if (isPipelineJargonUserBody(t)) continue;
    if (/^[A-Za-z가-힣]+\s+\d+$/.test(t) && !/:\d/.test(t) && t.length < 20) {
      // Allow "Genesis 6" style as soft anchor label
      if (!/genesis|창세기|gen\.?/i.test(t)) continue;
    }
    const key = canonicalPublicVerseKey(t);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(t);
  }
  return out;
}

/** Cap primary citations for user surface (Ask v1: ≤3 unique). */
export function capPrimaryVerseRefs(refs: string[], max = 3): string[] {
  return filterPublicVerseRefs(refs).slice(0, max);
}
