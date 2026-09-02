/** Client-safe S4 public surface filters (no Node imports). */
import { isStudioBoilerplateKo } from "./logosStudioBoilerplateV1";

const GEMATRIA_BULLET_RE =
  /combined_sum|vector_4d|hub_score|state16|Gematria_Pin|topology pin|mispar_/i;

/** Internal pipeline phrases — must never appear in Ring 0 S4 (Done-Product ceiling). */
export const PUBLIC_S4_STUB_PHRASE_RE =
  /Path\s*envelope|orphan\s*veto|concordance\s*pin|citation\s*lock\s*strip|Gematria_Pin|topology\s*pin|lemma:gnosis:|shared_lemma=|Lemma\s*연결\s*이웃\s*구절|envelope\s*concordance|path\s*token\s*preview/i;

/** Ops/pipeline jargon — hard-drop in Ring 0 public S4. */
export const PUBLIC_S4_OPS_JARGON_RE =
  /\bsend_gate\b|\blookup_only\b|\bwrong-?pack\b|\bprophecy\s*vote\b|\bharness\b|\bKPI\b|lemma:[a-z0-9_]+|citation[- ]?lock|path\s*envelope|Azure\s+citation|azure_distill|reading[_\s-]?pack|sidecar|stub\s*합선|Track\s*A|실매매|경로\s*마인드맵|product_all_ok|Done-?Harness|trust_face|LLM-OFF|RUNTIME-OFF|query-time|conflict\s*join|deterministic\s*synthesis|G3\s*hypo|idea\s*card|TSK\s*전량|open\s*LLM|why_question_assembled|:hebrew:|gematria\s*합선|topic-fitness\s*FAIL|상고팩|unmapped\s*HOLD|일반팩만|다층\s*독법|읽기\s*팩\s*[·・]\s*좌표\s*확장|동일\s*파이프라인|외부\s*합성\s*실패|이\s*폴백|\bretribution\b|\btheodicy_mystery\b|registry\s*densify|Golden-?200|GraphRAG|job_suffering|합선\s*벽|합선\s*금지/i;

export function containsPublicS4OpsJargon(text: string): boolean {
  return PUBLIC_S4_OPS_JARGON_RE.test(text || "");
}

export function scrubScholarHarnessSpeakKo(text: string): string {
  return (text || "")
    .replace(/why_question_assembled\s*=\s*(?:true|false)/gi, "")
    .replace(/via\s*·\s*:hebrew:[^\s)\]|,]*/gi, "")
    .replace(/:hebrew:[A-Za-z0-9_.:-]+/gi, "")
    .replace(/gematria\s*합선\s*없음\.?/gi, "")
    .replace(/\bretribution\s*(?:theology)?/gi, "응보")
    .replace(/\btheodicy_mystery\b/gi, "신정론·신비")
    .replace(/\bsend_gate\s*(?::\s*\w+)?/gi, "")
    .replace(/\blookup_only\b/gi, "")
    .replace(/\bwrong-?pack\b/gi, "")
    .replace(/\bprophecy\s*vote(?:\s*merge)?(?:\s*OFF)?\b/gi, "")
    .replace(/\bharness\b/gi, "")
    .replace(/\bKPI\b/g, "")
    .replace(/lemma:[a-z0-9_]+/gi, "")
    .replace(/citation[- ]?lock(?:ed)?(?:\s+evidence)?/gi, "본문 앵커")
    .replace(/path\s*envelope/gi, "")
    .replace(/product_all_ok\s*=?\s*\w*/gi, "")
    .replace(/query-time\s*conflict\s*join\s*\+\s*deterministic\s*synthesis\s*—?\s*/gi, "")
    .replace(/deterministic\s*synthesis/gi, "")
    .replace(/conflict\s*join/gi, "")
    .replace(/query-time/gi, "")
    .replace(/G3\s*hypo(?:\s*idea\s*card)?/gi, "")
    .replace(/idea\s*card/gi, "가설·상상 카드")
    .replace(/Done-?Harness/gi, "")
    .replace(/\btrust_face(?:_ko)?\b/gi, "")
    .replace(/\bLLM-OFF\b/gi, "")
    .replace(/\bRUNTIME-OFF\b/gi, "")
    .replace(/TSK\s*전량[·\s]*open\s*LLM\s*합성\s*아님\.?/gi, "")
    .replace(/TSK\s*전량/gi, "")
    .replace(/open\s*LLM\s*합성\s*아님\.?/gi, "")
    .replace(/^[^\n]*topic-fitness\s*FAIL[^\n]*$/gim, "")
    .replace(/^[^\n]*상고팩[^\n]*$/gim, "")
    .replace(/^[^\n]*unmapped\s*HOLD[^\n]*$/gim, "")
    .replace(/^[^\n]*Track\s*A[^\n]*$/gim, "")
    .replace(/Track\s*A[·\s]*실매매[^\n.]*(?:\.|$)/gi, "")
    .replace(/Track\s*A/gi, "")
    .replace(/실매매/gi, "")
    .replace(/topic-fitness/gi, "")
    .replace(/상고팩/gi, "")
    .replace(/(?:^|\n)\s*(?:#{1,6}\s*)?다층\s*독법(?:\s*\(\s*연구\s*프레임\s*\))?\s*/gim, "\n")
    .replace(/(?:^|\n)\s*(?:#{1,6}\s*)?읽기\s*팩\s*[·・]\s*좌표\s*확장\s*/gim, "\n")
    .replace(/(?:^|\n)\s*(?:#{1,6}\s*)?읽기\s*팩\s*[·・]\s*/gim, "\n")
    .replace(/학파\s*병렬[·\s]*citation\s*lock\s*보조\s*입력[^\n]*/gi, "")
    .replace(/학파\s*병렬[·\s]*본문\s*앵커\s*보조\s*입력[^\n]*/gi, "")
    .replace(/동일\s*파이프라인[^\n]*/gi, "")
    .replace(/외부\s*합성\s*실패\s*시\s*이\s*폴백[^\n]*/gi, "")
    .replace(/표시[·\s]*합성\s*깊이[^\n]*/gi, "")
    .replace(/\b파이프라인\b/gi, "")
    .replace(/\b폴백\b/gi, "")
    .replace(/reading[_\s-]?pack/gi, "")
    .replace(/azure_distill/gi, "")
    .replace(/\bsidecar\b/gi, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function stripPublicS4OpsJargon(text: string): string {
  return scrubScholarHarnessSpeakKo(text);
}

export function isPublicS4StubPhrase(text: string): boolean {
  const t = (text || "").trim();
  if (!t || t.length < 8) return true;
  if (GEMATRIA_BULLET_RE.test(t)) return true;
  if (PUBLIC_S4_STUB_PHRASE_RE.test(t)) return true;
  if (containsPublicS4OpsJargon(t)) return true;
  if (isStudioBoilerplateKo(t)) return true;
  return false;
}

export function firstNonStubLine(lines: string[]): string {
  for (const line of lines) {
    const t = line.trim();
    if (t && !isPublicS4StubPhrase(t)) return t;
  }
  return "";
}
