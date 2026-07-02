/**
 * INV-03 + display readability — public strip, narrative paragraphs, reading pack accordion.
 * Run: npx tsx scripts/smoke-logos-ask-display-invariants-v1.ts
 */
import {
  buildPublicInquiryDisplayModel,
  formatPublicNarrativeParagraphs,
  meetsDoneProductGoldenRubric,
  meetsPublicNarrativeQuality,
  parseReadingPackSections,
  splitS4PublicBody,
  stripPublicResearchTags,
} from "../src/lib/logosInquiryAskDisplayV1.ts";
import { applyInquiryS4QualityGate } from "../src/lib/logosInquiryReportV1.ts";
import {
  buildLogosInquiryReport,
  evaluateLogosInquiryIntake,
  DEFAULT_FREEZE_LEXICON_META,
} from "../src/lib/logosInquiryReportV1.ts";
import { buildRev21NewCreationThematicAnswerKo } from "../src/lib/logosInquiryVerseThematicV1.ts";
import { detectPsalm23Topic } from "../src/lib/logosStudioQueryTopicGuardV1.ts";

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

const stubBody = "Path envelope concordance pin for orphan veto routing.";
const gated = applyInquiryS4QualityGate({
  body: stubBody,
  bullets: [stubBody],
  verseRefs: ["Job.28.12", "Ps.23.1"],
  query: "시편 23편 — 목자 비유와 학파별 해석",
});
assert(!/Path\s*envelope|orphan\s*veto/i.test(gated.body), "S4 stub phrases remain after gate");
assert(/Ps\.23|시편\s*23|목자/i.test(gated.body), "Psalm 23 fallback missing");

const golden = meetsDoneProductGoldenRubric({
  query: "시편 23편 — 목자 비유와 학파별 해석",
  s4Body: gated.body,
  verseRefs: ["Ps.23.1", "Ps.23.4"],
  schoolGroups: [
    {
      schools: [
        { school_tier: "historical", interpretation_ko: "목자 은유" },
        { school_tier: "literary", interpretation_ko: "신뢰·길 안내" },
      ],
    },
  ],
});
assert(golden.stub_free, "golden stub_free");
assert(golden.product_ok, "golden product_ok");
assert(detectPsalm23Topic("시편 23편 — lemma·경로"), "psalm23 detect smoke question");

const schoolQuery = "시편 23편 — 목자 비유와 학파별 해석";
const schoolReport = buildLogosInquiryReport(
  {
    answer: "시편 23편 목자 비유를 citation lock 중심으로 요약합니다.",
    path: { verse_refs: ["Ps.23.1", "Ps.23.4"], steps: [], node_ids: [], note_ko: null, bridges_matched: null },
    research_only: true,
    non_gating: true,
    send_gate: "HOLD",
    preset_id: "topic_ps_23_anchor",
  } as import("../src/lib/logosResearchStudioV1.ts").StudioQueryPayload,
  schoolQuery,
  evaluateLogosInquiryIntake(schoolQuery, "logos", "reports"),
  DEFAULT_FREEZE_LEXICON_META,
);
assert((schoolReport.sections.S3.groups?.length ?? 0) >= 1, "ps23 school fallback groups");
assert(
  (schoolReport.sections.S3.groups?.[0]?.schools?.length ?? 0) >= 2,
  "ps23 school fallback rows",
);

console.log("[smoke-logos-ask-display-invariants-v1] passed.");
