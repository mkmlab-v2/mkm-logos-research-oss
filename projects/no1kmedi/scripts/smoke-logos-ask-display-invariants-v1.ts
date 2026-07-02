/**
 * INV-03 + display readability — public strip, narrative paragraphs, reading pack accordion.
 * Run: npx tsx scripts/smoke-logos-ask-display-invariants-v1.ts
 */
import {
  buildPublicInquiryDisplayModel,
  formatPublicNarrativeParagraphs,
  meetsPublicNarrativeQuality,
  parseReadingPackSections,
  splitS4PublicBody,
  stripPublicResearchTags,
} from "../src/lib/logosInquiryAskDisplayV1.ts";
import { buildRev21NewCreationThematicAnswerKo } from "../src/lib/logosInquiryVerseThematicV1.ts";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const sample = `[HYPO] 질문 본문입니다.

### Reading pack
**Pack:** test

research_only · send_gate: HOLD · [NON_GATING]`;

const stripped = stripPublicResearchTags(sample);
assert(!/\[HYPO\]/i.test(stripped), "HYPO tag remains");
assert(!/\[NON_GATING\]/i.test(stripped), "NON_GATING remains");
assert(!/research_only/i.test(stripped), "research_only remains");
assert(!/send_gate/i.test(stripped), "send_gate remains");

const { narrative } = splitS4PublicBody(sample);
assert(narrative.includes("질문 본문"), "narrative content lost");
assert(!/\[HYPO\]/i.test(narrative), "narrative still has HYPO");

const packSample = `666·적그리스도 — Pack 3종 병렬.

### 1. 666 · 짐승의 수 (Rev.13)
χξϛ(666) — 지혜 있는 자의 계산.

### 2. 요한서신 적그리스도
1John.2.18 앵커 병렬.`;

const sections = parseReadingPackSections(packSample);
assert(sections.length >= 2, "reading pack sections");
assert(/666|짐승/.test(sections[0].title), "first pack title");

const rev21 = buildRev21NewCreationThematicAnswerKo("요한계시록 21장 새 하늘과 새 땅의 상징은?");
const revParas = formatPublicNarrativeParagraphs(rev21);
assert(revParas.length >= 2, "rev21 narrative paragraphs");
const quality = meetsPublicNarrativeQuality(rev21);
assert(quality.narrative_ok, "rev21 meets public narrative quality");

const model = buildPublicInquiryDisplayModel(`${rev21}\n\n---\n\n${packSample}`);
assert(model.narrativeParagraphs.length >= 2, "display model narrative");
assert(model.readingPackSections.length >= 1, "display model packs");

console.log("[smoke-logos-ask-display-invariants-v1] passed.");
