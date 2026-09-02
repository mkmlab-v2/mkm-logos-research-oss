/**
 * Topical freeform inquiry bootstrap (Done-Product ceiling, research_only).
 * Soft-match may clear a weak preset hit; friend-floor research freeform still
 * proceeds via thematic synthesis + honest control banner — not silent hub landings.
 *
 * D-FREEFORM-HONEST-1 policy:
 * - Softmatch 422 = true nonsense / empty / attack only
 * - Clear topical/research freeform (bible code, gematria, 원어, faith, theology Q)
 *   → HTTP 200 + essay with MKM rules ([HYPO] / soft citation / NON_GATING)
 * - antichrist_666 / 666 person-decode dogma traps → hub thematic bootstrap
 *   (topic_1john / antichrist_666; Rev21 pack leakage forbidden; no single decode)
 * - Product-risk offtopic (weather / stock-price / medical-advice) → HTTP 200
 *   OFFTOPIC redirect card (not fake theology essay)
 * - Weak citation → visible Korean banner, never raw machine codes
 */
import {
  hubPrimaryVerseRefs,
  matchGoldenHubQuery,
} from "./logosGolden200HubMatchV1";
import { shouldDeferFaithPackToGeneral, isBareGospelAmbiguousQuery } from "./logosAskConfidenceGateV1";
import {
  BIB_DYN_ASK_PRIMARY_PRESET_ID,
  BIB_DYN_ASK_PRIMARY_QUERY_MODE,
  BIB_DYN_PRIMARY_BANNER_KO,
  buildBibDynPrimaryAnswerKo,
  extractBibDynPatternVerseRefs,
  matchBibDynPatternForAskPrimary,
} from "./logosBibDynPatternAskOptInV1";
import {
  buildDecalogueThematicAnswerKo,
  resolveDecaloguePrimaryRefs,
  resolveDecalogueQueryClassV1,
  type DecalogueQueryClassV1,
} from "./logosCommandmentIntentDetectV1";
import { buildTabernacleLedgerLookupInjectBlockKo } from "./logosAskLedgerLookupPackV1";
import openbibleDivinationAnchors from "@/data/logos_ask_openbible_divination_anchors_v1.json";
import {
  detectJobSufferingTopic,
  detectJohn316Topic,
  detectPsalm23Topic,
} from "./logosInquiryTopicDetectV1";
import {
  buildJobSufferingThematicAnswerKo,
  buildJohn316ThematicAnswerKo,
  buildPsalm23ShepherdThematicAnswerKo,
} from "./logosInquiryDepthThematicBuildersV1";
import { mergeDivinationNtBridgeRefs } from "./logosAskDeclaredSectionGateV1";
import { applyArmAXrefShrinkV1 } from "./logosAskArmAXrefPolicyV1";
import {
  isDrawerKnownWithoutPack,
  resolveAskDrawerV1,
} from "./logosAskDrawerRouterV1";
import { tryBuildRemainingDrawerL2Bootstrap, tryBuildDrawerL2LateSoftBootstrap } from "./logosAskDrawerL2PacksV1";
import { parseKoRefExplicitV1 } from "./logosAskKoRefExplicitV1";
import { formatVerseRefKoV1 } from "./logosAskVerseLabelKoV1";

/** Prose ref list for freeform hub bodies — KO book names at source (not scrub-only). */
function joinPrimaryRefsKoV1(refs: string[], max = 6): string {
  return refs
    .slice(0, max)
    .map((r) => formatVerseRefKoV1(r) || r)
    .filter(Boolean)
    .join(" · ");
}

export const FREEFORM_TOPICAL_PRESET_ID = "dynamic_topical_freeform";
export const FREEFORM_OFFTOPIC_PRESET_ID = "dynamic_offtopic_redirect";

/** Visible when citation lock is soft / advisory — never machine codes. */
export const FREEFORM_WEAK_CITATION_BANNER_KO =
  "근거 연결이 약합니다 · 연구 참고";

/** Product honesty: offtopic is in-scope UX, not softmatch 422. */
export const FREEFORM_OFFTOPIC_BANNER_KO =
  "범위 밖 · MKM 닻은 성경 연구 Ask입니다 (만능 챗봇 아님)";

/**
 * P0-2 unmatched → short citation HOLD (no long wisdom/anxiety fake essay).
 * Must never serve Deut/Prov/2Tim/Rev generic theology pack as “the answer”.
 * Legacy G3 idea-card names kept for control-grade mapping / smoke aliases.
 */
export const FREEFORM_G3_IDEA_BANNER_KO = "본문 앵커 없음 · 구절·주제로 좁혀 주세요";
export const FREEFORM_G3_IDEA_PRESET_ID = "dynamic_g3_hypo_idea_card";
export const FREEFORM_G3_IDEA_QUERY_MODE =
  "inquiry_thematic_g3_hypo_idea_card" as const;
/** Alias — product copy for no-citation HOLD (same banner as G3 floor). */
export const FREEFORM_NO_CITATION_HOLD_BANNER_KO = FREEFORM_G3_IDEA_BANNER_KO;

/** Layer-1 unmapped concept — honest null (no generic/faith swallow). */
export const FREEFORM_UNMAPPED_CONCEPT_QUERY_MODE =
  "inquiry_unmapped_concept_hold" as const;
export const FREEFORM_UNMAPPED_CONCEPT_BANNER_KO =
  "본문 앵커 없음 · 구절·주제로 좁혀 주세요";
export const UNMAPPED_CANDIDATE_QUEUE_JSONL =
  "docs/final/artifacts/logos_ask_unmapped_candidate_queue_v1.jsonl";

/** Forbidden wrong-pack refs for unmatched life/freeform (strategy P0-2). */
export const FORBIDDEN_UNMATCHED_THEOLOGY_PACK_REFS = [
  "Deut.4.2",
  "Prov.25.2",
  "2Tim.3.16",
  "Rev.13.18",
  "Eccl.12.12",
  "John.5.39",
  "Acts.17.11",
] as const;
/** Candidate verse refs — idol/image/wisdom/beast/tool metaphors (not dogma decode). */
export const AI_SOCIETY_SYMBOLISM_PRIMARY_REFS = [
  "Gen.1.26",
  "Exod.20.4",
  "Prov.8.1",
  "Prov.8.22",
  "Dan.2.43",
  "Rev.13.15",
  "1Cor.8.4",
  "Eccl.7.29",
] as const;

/** Faith / belief freeform anchors — parallel schools, never single dogma decode. */
export const BIBLICAL_FAITH_PRIMARY_REFS = [
  "Heb.11.1",
  "John.3.16",
  "Rom.1.17",
  "Rom.10.9",
  "Eph.2.8",
  "Jas.2.17",
  "Mark.9.24",
  "Hab.2.4",
] as const;

/**
 * Tabernacle / 성막 noun-domain anchors (Exod 25–40 · Heb 9).
 * Must not be swallowed by bare soteriology pack when Q names 성막.
 * research_only · NON_GATING · ≠ product DONE.
 */
export const TABERNACLE_NOUN_DOMAIN_PRIMARY_REFS = [
  "Exod.25.8",
  "Exod.27.1",
  "Exod.30.1",
  "Exod.40.34",
  "Heb.9.1",
  "Heb.9.11",
  "Heb.9.12",
] as const;

/** Optional salvation-parallel soft refs when Q also mentions 구원 — never alone. */
export const TABERNACLE_SALVATION_PARALLEL_REFS = [
  "John.14.6",
  "Heb.10.19",
  "Heb.10.20",
] as const;

const TABERNACLE_NOUN_DOMAIN_RE =
  /성막|회막|tabernacle|성소\s*기구|성막의|출애굽기\s*2[5-9]|출애굽기\s*3[0-9]|출애굽기\s*40|히브리서\s*9|heb\.?\s*9/i;

/**
 * Soft anchors for general theology / bible-code research freeform.
 * Advisory only — not verse-exact proof of modern claims.
 */
export const RESEARCH_THEOLOGY_PRIMARY_REFS = [
  "Deut.4.2",
  "Prov.25.2",
  "Eccl.12.12",
  "2Tim.3.16",
  "Rev.13.18",
  "John.5.39",
  "Acts.17.11",
] as const;

/**
 * Hell / eternal-punishment research freeform — topic anchors only.
 * Must NOT embed Deut.4.2+Prov.25.2+2Tim.3.16 core triple (wrong-pack).
 */
export const RESEARCH_THEOLOGY_HELL_PRIMARY_REFS = [
  "Matt.25.46",
  "Rev.20.14",
  "Rev.20.10",
  "Mark.9.48",
  "2Thess.1.9",
] as const;

/**
 * Angel / free-will / fallen-angel research freeform — topic anchors only.
 * Must NOT use Deut.4.2+Eccl.12.12+John.5.39 generic "search scripture" pack.
 */
export const RESEARCH_THEOLOGY_ANGEL_FREEWILL_PRIMARY_REFS = [
  "Jude.6",
  "2Pet.2.4",
  "Rev.12.7",
  "Rev.12.9",
  "Matt.25.41",
  "Heb.1.14",
] as const;

/** Bare 「십자가의 의미」 soft anchors — not john19/criminal curated hubs. */
export const RESEARCH_THEOLOGY_CROSS_MEANING_PRIMARY_REFS = [
  "1Cor.1.18",
  "Gal.6.14",
  "Phil.2.8",
  "John.3.14",
  "Rom.5.8",
] as const;

/**
 * Divination / fortune-telling / 사주·관상·타로 research freeform — topic anchors.
 * Prefer OpenBible+lexical fixture when present (thin generalization); else static pack.
 * Must NOT fall back to Deut.4.2+Eccl.12.12+John.5.39 generic "search scripture" pack.
 */
export const RESEARCH_THEOLOGY_DIVINATION_PRIMARY_REFS = [
  "Deut.18.10",
  "Deut.18.11",
  "Deut.18.12",
  "Lev.19.26",
  "Lev.19.31",
  "Isa.47.13",
  "Acts.16.16",
  "Gal.5.20",
] as const;

/**
 * Prayer / 주기도 / 쉬지 말고 기도 — topic anchors.
 * Must NOT collapse to bare faith pack (Heb.11 / John.3.16) when Q noun-domain is 기도.
 */
export const RESEARCH_THEOLOGY_PRAYER_PRIMARY_REFS = [
  "Matt.6.9",
  "Matt.6.10",
  "Matt.6.11",
  "1Thess.5.17",
  "Phil.4.6",
  "Luke.18.1",
  "John.14.13",
] as const;

/** Psalm 23 shepherd comfort — freeform bootstrap parity with studio curated path. */
export const PSALM23_SHEPHERD_FREEFORM_PRIMARY_REFS = [
  "Ps.23.1",
  "Ps.23.4",
  "Ps.23.5",
  "Ps.23.6",
] as const;

/** Job suffering — include classic Job.1.21 / Job.42.5 + studio family. */
export const JOB_SUFFERING_FREEFORM_PRIMARY_REFS = [
  "Job.1.1",
  "Job.1.8",
  "Job.1.21",
  "Job.2.10",
  "Job.42.5",
  "Job.42.7",
] as const;

function resolveDivinationAnchorsFromOpenBibleFixture(): string[] {
  const refs = (openbibleDivinationAnchors as { verse_refs?: string[] })?.verse_refs;
  if (!Array.isArray(refs) || refs.length === 0) return [];
  const base = refs.map((r) => String(r).trim()).filter(Boolean);
  // OT OpenBible expand alone can omit NT — always merge thin NT bridge.
  return mergeDivinationNtBridgeRefs(base).slice(0, 10);
}

const HELL_LITERAL_TOPIC_RE =
  /지옥.*문자|문자.*지옥|영원히\s*불|지옥은|eternal\s*hell|literal\s*hell|지옥.*영원/i;

/** 사주·관상·타로·점술 — on-domain vs generic theology soft pack. */
const DIVINATION_TOPIC_RE =
  /사주|관상|타로|점술|복술|무당|점쟁이|신접|박수|초혼|점\s*치|운세|별점|점성|제사를?\s*지내|차례를?\s*지내|조상\s*제사|명절.{0,12}제사|ancestral\s*rites?|divination|fortune[\s-]?tell|horoscope|tarot|astrology|necroman|witchcraft|sorcer/i;

/** 기도·주기도·간구 — noun-domain vs bare faith pack swallow. */
const PRAYER_TOPIC_RE =
  /어떻게\s*기도|기도해|주기도|간구|중보\s*기도|쉬지\s*말고\s*기도|기도했는데|기도\s*응답|응답이\s*없|하나님의\s*뜻|뜻\s*분별|lord'?s\s*prayer|pray\s*without\s*ceasing|unanswered\s*prayer|(?:기도(?:는|가|를|의|란|에|로)?\s*(?:성경|어떻|무엇|그리|의미|응답|방법)|성경.{0,12}기도|기도.{0,12}(?:그리|의미|응답|방법)|how\s+(?:does\s+)?(?:the\s+)?bible.{0,24}pray|prayer.{0,16}(?:bible|scripture))/i;

/** Angels + free will / fall / satan choice — topical citation routing. */
const ANGEL_FREEWILL_TOPIC_RE =
  /천사.{0,24}(?:자유\s*의지|자유의지|선택|타락)|(?:자유\s*의지|자유의지|선택|타락).{0,24}천사|타락한\s*천사|거룩한\s*천사|fallen\s*angel|angels?\s+(?:free\s*will|choice|fall)|free\s*will\s+of\s+angels?|사탄.{0,16}천사|천사.{0,16}사탄|마귀.{0,12}타락/i;

/** Bare cross/meaning without specific passion hub markers (blood-water / criminals). */
const BARE_CROSS_MEANING_RE =
  /십자가(?:의)?\s*의미|의미(?:는|가)?\s*십자가|cross(?:\s+of\s+christ)?(?:'s)?\s*meaning|meaning\s+of\s+(?:the\s+)?cross/i;

const TOPICAL_AI_RE =
  /\bai\b|a\.i\.|인공지능|생성형|llm|챗봇|로봇|기계\s*지능|artificial\s*intelligence|machine\s*learning|chatgpt|claude/i;
const TOPICAL_SYMBOL_RE =
  /상징|비유|은유|우상|형상|지혜|짐승|도구|idol|image|wisdom|beast|metaphor|symbol|parable|analogy/i;
const TOPICAL_SOCIETY_RE =
  /사회|인간|미래|변화|문명|노동|윤리|society|human|future|change|civilization|labor|ethic/i;
const TOPICAL_BIBLE_FRAME_RE = /성경|성서|bible|성서적|성서\s*안|말씀|구약|신약|scripture/i;
const FAITH_TOPIC_RE =
  /신앙|믿음|구원|기도|회개|은혜|십자가|부활|하나님|하느님|예수|그리스도|성령|교회|죄사함|칭의|의인|복음|faith|belief|believe|salvation|jesus|christ|grace|prayer|gospel/i;

/**
 * Architecture friend floor (not keyword whitelist): bible/theology research frame.
 * Catches bible-code / general theology / 원어 research Qs without requiring verse numbers.
 */
const RESEARCH_THEOLOGY_FRAME_RE =
  /성경|성서|바이블|bible|scripture|신학|theology|원어|히브리|헬라|그리스어|아람|게마트리아|gematria|교리|묵시|예언|복음서|구약|신약|canon|canonical|els|equidistant|토라|torah|사도|모세|시편|이사야|요한|마태|마가|누가|로마서|계시록|말씀|하나님|하느님|예수|그리스도|성령|교회|구원|창조|종말|신앙|믿음|천국|천당|지옥|영혼|영생|낙원|사후|부활|소멸|피조물|동물|생물|eden|heaven|hell|soul|afterlife|creature|animal/i;
const RESEARCH_QUESTION_SHAPE_RE =
  /(?:는가|인가|일까|있을까|있는가|없는가|것인가|것인가\?|무엇인가|어떤|왜|어떻게|의미|존재|진짜|사실|가능|타당한가|옳은가|틀린가|해주세요|알려|설명|궁금|\?|？)/;
const BIBLE_CODE_TOPIC_RE =
  /바이블\s*코드|bible\s*codes?|성서\s*암호|성경\s*암호|equidistant\s*letter|els\b|토라\s*코드|torah\s*codes?/i;
const GEMATRIA_MEANING_FREEFORM_RE =
  /gematria|게마트리아|수비학|666\s*의미|수학화|원어.*수학|수학.*원어|원어를\s*수학/i;

/** Gematria / math-original freeform — local detect (no logosInquiryVerseThematicV1 import; cycle). */
export function detectGematriaMeaningFreeformTopic(query: string): boolean {
  return GEMATRIA_MEANING_FREEFORM_RE.test(String(query || "").toLowerCase());
}

/** True nonsense / abuse — keep softmatch 구체화 UX. */
const NONSENSE_RE =
  /^(?:(?:asdf|qwer|zxcv|test|xxx|foo|bar|baz|ㅋㅋ+|ㅎㅎ+|ㅁㄴㅇㄹ)+[\d!?.~]*|asdfqwer|qwerty|zxcvbnm)$/i;
/** Attack / injection-shaped freeform — refuse essay bootstrap. */
const ATTACK_RE =
  /(?:ignore\s+previous|system\s*prompt|jailbreak|<\/?\s*script|DROP\s+TABLE|union\s+select)/i;

/**
 * Product-risk offtopic (Done-Product honesty): weather / market price / clinical advice.
 * Must not land on general-theology essay bootstrap. Softmatch 422 stays nonsense-only.
 * Bible/faith framed Qs stay on research path (e.g. 「성경은 재물에 대해」).
 */
export type ProductRiskOfftopicClass = "weather" | "stock_market" | "medical" | "gambling";

const WEATHER_OFFTOPIC_RE =
  /(?:오늘|내일|모레|주말)(?:\s*[가-힣A-Za-z0-9]{1,12})?\s*날씨|날씨\s*(?:어때|어떠|좋|나쁨|예보)|weather\b|기온|체감\s*온도|몇\s*도(?:야|인가요)|우산\s*챙|비\s*올까|눈\s*올까|미세먼지|황사/i;

const STOCK_OFFTOPIC_RE =
  /비트코인|이더리움|이더\b|코인\b|암호화폐|crypto\b|주식|코스피|코스닥|nasdaq|나스닥|주가|매수|매도|투자\s*추천|수익률|(?:내일|오늘|이번\s*주).{0,12}(?:오를|내릴|상승|하락)(?:까|까요|지)|(?:오를|내릴)까(?:요)?/i;

const MEDICAL_OFFTOPIC_RE =
  /(?:당뇨|고혈압|고지혈|갑상선|위염|감기|독감|암).{0,24}(?:약|복용|처방)|약\s*(?:뭐|무엇|어떤)|(?:어떤|무슨)\s*약|뭐\s*먹으면\s*좋|복용|처방(?:해|받)|진단\s*(?:해|좀)|치료법|병원\s*(?:가|가야)|증상(?:인데|이)?\s*(?:뭐|무엇|어떤)?\s*약|medical\s*advice|처방전/i;

const GAMBLING_OFFTOPIC_RE =
  /로또|복권|토토|스포츠토토|카지노|도박|베팅|당첨\s*번호|lottery|gambling|slot\s*machine/i;

function hasBibleOrFaithResearchFrame(query: string): boolean {
  return (
    RESEARCH_THEOLOGY_FRAME_RE.test(query) ||
    FAITH_TOPIC_RE.test(query) ||
    TOPICAL_BIBLE_FRAME_RE.test(query) ||
    BIBLE_CODE_TOPIC_RE.test(query)
  );
}

export function classifyProductRiskOfftopic(query: string): ProductRiskOfftopicClass | null {
  const q = query.trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return null;
  // Market tipster via Bible still offtopic — bible frame must NOT swallow this.
  // Gate0 abstain seed: 「코스피가 오를지 성경으로」
  if (
    STOCK_OFFTOPIC_RE.test(q) &&
    /비트코인|이더리움|이더\b|코인\b|암호화폐|crypto\b|주식|코스피|코스닥|nasdaq|나스닥|주가|매수|매도|투자|수익률/i.test(
      q,
    ) &&
    /(?:오를|내릴|상승|하락|예측|알려|차트|해석)/i.test(q)
  ) {
    return "stock_market";
  }
  // Gambling tipster via Bible — held-out batch2: 「로또 당첨번호 성경으로」
  // Ethics/sin FAQ (「도박은 죄인가요?」·「성경은 도박을」) stays research path → wealth hub.
  if (
    GAMBLING_OFFTOPIC_RE.test(q) &&
    /(?:알려|당첨|번호|예측|추천)/i.test(q) &&
    !/(?:죄|윤리|성경|성서|bible|sin\b|ethic)/i.test(q)
  ) {
    return "gambling";
  }
  // Pastoral / theology freeform wins over other product-risk heuristics
  if (hasBibleOrFaithResearchFrame(q)) return null;
  // Sin/ethics framed gambling without tipster tokens → research (not offtopic redirect)
  if (
    GAMBLING_OFFTOPIC_RE.test(q) &&
    /(?:죄|윤리|성경|성서|bible|sin\b|ethic)/i.test(q) &&
    !/(?:알려|당첨|번호|예측|추천)/i.test(q)
  ) {
    return null;
  }
  if (WEATHER_OFFTOPIC_RE.test(q)) return "weather";
  if (MEDICAL_OFFTOPIC_RE.test(q)) return "medical";
  if (GAMBLING_OFFTOPIC_RE.test(q)) return "gambling";
  // Stock: require a market token OR (price-direction + marketish cue already in RE)
  if (STOCK_OFFTOPIC_RE.test(q)) {
    // Avoid lone 「오를까」 pastoral false positives without market noun
    if (
      /비트코인|이더리움|이더\b|코인\b|암호화폐|crypto\b|주식|코스피|코스닥|nasdaq|나스닥|주가|매수|매도|투자|수익률/i.test(
        q,
      )
    ) {
      return "stock_market";
    }
  }
  return null;
}

/**
 * Matching-layer abstain (HOLD=[]) — personalize fortune / tipster.
 * Distinct from research 「성경에서 사주·점술은 어떻게」 noun-domain.
 */
const PERSONAL_SAJU_ABSTAIN_RE =
  /(?:제|내|나의)\s*사주|사주에\s*맞는|사주\s*에\s*맞는|사주로\s*(?:점|알려|추천)|사주\s*풀이|(?:제|내|나의)\s*관상|관상에\s*맞는|관상\s*에\s*맞는|(?:제|내|나의)\s*(?:직장)?운(?:세)?|운세\s*구절|직장운|(?:제|내|나의)\s*타로|타로\s*결과.{0,16}맞는|타로.{0,16}맞는\s*(?:성경|구절)|타로로\s*(?:오늘\s*)?운세|타로.{0,16}운세|운세\s*보고.{0,24}(?:성경|구절)|tarot.{0,16}(?:fortune|horoscope|verse|bible)|태어난\s*시간.{0,40}(?:이름|성경)|이름(?:이랑|과|으로).{0,40}(?:맞는\s*)?성경\s*인물|저한테\s*맞는\s*성경\s*인물|나한테\s*맞는\s*성경\s*인물/i;

export function detectPersonalSajuMatchingAbstain(query: string): boolean {
  const q = String(query || "").trim();
  if (!q) return false;
  // Research framing wins: 「성경에서 사주…어떻게」 is divination noun-domain, not abstain.
  if (/성경에서|성서에서|bible\s*on|how\s*(?:does|do)\s*(?:the\s*)?bible/i.test(q) && /취급|해석|다루|말하/i.test(q)) {
    return false;
  }
  return PERSONAL_SAJU_ABSTAIN_RE.test(q);
}

export function detectMatchingAbstainHold(query: string): boolean {
  return detectPersonalSajuMatchingAbstain(query);
}

/** Comfort · presence / fear — Isa.41 / Ps.23.4 family (before bare faith pack). */
export const COMFORT_PRESENCE_PRIMARY_REFS = [
  "Matt.6.25",
  "Matt.6.33",
  "Isa.41.10",
  "Ps.23.4",
  "Deut.31.6",
  "Phil.4.6",
] as const;

/** Comfort · sorrow — lament / presence / comfort family (pastoral soft_grief). */
export const COMFORT_SORROW_PRIMARY_REFS = [
  "2Cor.1.3",
  "2Cor.1.4",
  "Ps.34.18",
  "Ps.13.1",
  "Ps.22.1",
  "Matt.5.4",
  "Matt.11.28",
  "Job.3.11",
  "Ps.147.3",
] as const;

/** Queue→map rotation packs (batch2 commander_frozen gold families). */
export const GUILT_FORGIVENESS_PRIMARY_REFS = [
  "1John.1.9",
  "Rom.8.1",
  "Ps.103.12",
  "Ps.51.1",
  "Heb.8.12",
] as const;
export const REPENTANCE_PRIMARY_REFS = [
  "Acts.3.19",
  "2Cor.7.10",
  "Luke.15.7",
  "1John.1.9",
  "Joel.2.13",
] as const;
export const INTERCESSION_PRAYER_PRIMARY_REFS = [
  "1Tim.2.1",
  "Job.42.10",
  "Jas.5.16",
  "Eph.6.18",
] as const;
export const LOVE_ENEMY_PRIMARY_REFS = [
  "Matt.5.44",
  "Rom.12.20",
  "Luke.6.27",
  "Prov.25.21",
] as const;
export const WEALTH_STEWARDSHIP_PRIMARY_REFS = [
  "1Tim.6.10",
  "Matt.6.24",
  "Luke.12.15",
  "Prov.11.28",
  "Heb.13.5",
  "Mal.3.10",
] as const;
export const SPEECH_GUARD_PRIMARY_REFS = [
  "Jas.1.19",
  "Jas.3.5",
  "Prov.15.1",
  "Eph.4.29",
  "Prov.18.21",
  "Prov.12.22",
] as const;
/** Commander ACK 승인한다 · Level-2 packs for known-no-pack drawers (HQ seeds frozen as soft). */
export const HOLY_SPIRIT_PRIMARY_REFS = [
  "John.14.26",
  "Rom.8.9",
  "Gal.5.22",
  "Acts.1.8",
  "1Cor.12.30",
] as const;
export const CHURCH_FELLOWSHIP_PRIMARY_REFS = [
  "Acts.2.42",
  "Heb.10.25",
  "1Cor.12.12",
  "Eph.4.4",
] as const;
export const WORSHIP_THANKSGIVING_PRIMARY_REFS = [
  "Ps.100.4",
  "Ps.95.1",
  "John.4.23",
  "Heb.13.15",
] as const;
export const PATIENCE_TRIALS_PRIMARY_REFS = [
  "Jas.1.2",
  "Jas.1.3",
  "Rom.5.3",
  "Rom.5.4",
  "1Pet.1.6",
] as const;

const COMFORT_PRESENCE_RE =
  /힘들\s*때|곁에\s*계신|하나님이\s*곁|두려워할\s*때|불안할\s*때|붙잡을\s*구절|임재|함께\s*하(?:심|시)/i;
/** Grief / lament / anger-at-God pastoral — colloquial soft_grief included. */
const COMFORT_SORROW_RE =
  /슬픔\s*중|위로가\s*되는|위로\s*말씀|슬플\s*때|애통|애도|위로해|상실|눈물|탄식|사별|별세|돌아가신|악몽|아이에게\s*읽어|읽어주면\s*좋은\s*말씀|(?:가족|부모|아이|남편|아내|자식|사람).{0,12}잃|잃(?:고|어|은).{0,24}(?:가족|부모|아이|남편|아내|자식|사람)|하나님(?:이|께|을|한테)?.{0,16}원망|원망스러|화가\s*나(?:요|서|다)?|왜\s*하나님|grief|lament|bereave|mourn(?:ing)?/i;
const GUILT_FORGIVENESS_RE =
  /죄책감|양심의\s*가책|죄책|용서받을\s*수|사함|양심이\s*괴로|괴로운\s*양심|양심.{0,8}위로|confession\s*of\s*sin|guilt/i;
const REPENTANCE_TOPIC_RE =
  /회개(?:는|를|하|란)?|repent(?:ance|ing)?|돌이키/i;
const INTERCESSION_PRAYER_RE =
  /위해\s*기도|중보|다른\s*사람.{0,12}기도|남을\s*위해\s*기도|intercess/i;
const LOVE_ENEMY_RE =
  /원수를\s*사랑|사랑하라.*원수|미워하는\s*사람.{0,12}사랑|사랑하.{0,16}미워|love\s*(?:your\s*)?enem/i;
const WEALTH_STEWARDSHIP_RE =
  /재물|탐심|돈에\s*대해|부에\s*대해|돈\s*사랑|돈을\s*사랑|wealth|mammon|riches|탐내|십일조|헌금|드릴\s*게\s*없어서|도박은\s*죄|성경.{0,16}도박|도박.{0,16}(?:성경|성서|죄)|gambling.{0,16}sin|bible.{0,16}gambling/i;
const SPEECH_GUARD_RE =
  /정직|거짓\s*말|거짓\s*서류|거짓\s*증|서명하(?:라|라고)|말조심|혀를\s*삼|말에\s*관한|혀의\s*죄|말이\s*화|말의\s*화|혀.{0,6}화|speech|tame\s*the\s*tongue|말의\s*힘/i;
const HOLY_SPIRIT_RE =
  /성령\s*충만|성령의\s*열매|성령(?:이란|은|이\s*무엇|이\s*누구|을?\s*못\s*받)|보혜사|방언|holy\s*spirit|tongues?/i;
const CHURCH_FELLOWSHIP_RE =
  /교회(?:란|는|가\s*왜|의\s*의미)|성도의\s*교제|church\s*(?:is|mean|why)|성경적(?:으로)?.{0,8}교회/i;
const WORSHIP_THANKSGIVING_RE =
  /감사하는\s*마음|감사\s*(?:구절|말씀)|예배(?:의\s*뜻|란)|thanksgiving|worship/i;
const PATIENCE_TRIALS_RE =
  /인내(?:에|란|는|를|하)|patience|endure/i;

export function detectComfortPresenceTopic(query: string): boolean {
  return COMFORT_PRESENCE_RE.test(String(query || "").trim());
}

export function detectComfortSorrowTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (
    detectComfortPresenceTopic(q) &&
    !/슬픔|위로가\s*되는|애통|애도|악몽|아이에게\s*읽어/i.test(q)
  )
    return false;
  return COMFORT_SORROW_RE.test(q);
}

export function detectGuiltForgivenessTopic(query: string): boolean {
  return GUILT_FORGIVENESS_RE.test(String(query || "").trim());
}

export function detectRepentanceTopic(query: string): boolean {
  return REPENTANCE_TOPIC_RE.test(String(query || "").trim());
}

export function detectIntercessionPrayerTopic(query: string): boolean {
  return INTERCESSION_PRAYER_RE.test(String(query || "").trim());
}

export function detectLoveEnemyTopic(query: string): boolean {
  return LOVE_ENEMY_RE.test(String(query || "").trim());
}

export function detectWealthStewardshipTopic(query: string): boolean {
  const q = String(query || "").trim();
  // Avoid decalogue covet false steal — wealth Q needs bible/재물/십일조/도박윤리 frame
  if (
    !/재물|탐심|돈|부|wealth|mammon|riches|탐내|십일조|헌금|도박|gambling/i.test(q)
  ) {
    return false;
  }
  return WEALTH_STEWARDSHIP_RE.test(q);
}

export function detectSpeechGuardTopic(query: string): boolean {
  const q = String(query || "").trim();
  // honesty_integrity owns 「정직」 pastoral; keep speech_guard for tongue/lie packing.
  if (/정직에\s*대한|정직이란|정직한\s*삶|정직과\s*거짓|정직\s*구절|biblical\s*honesty|\bintegrity\b/i.test(q)) {
    return false;
  }
  if (matchGoldenHubQuery(q)?.hub_id === "honesty_integrity") return false;
  return SPEECH_GUARD_RE.test(q);
}

export function detectHolySpiritTopic(query: string): boolean {
  return HOLY_SPIRIT_RE.test(String(query || "").trim());
}

export function detectChurchFellowshipTopic(query: string): boolean {
  return CHURCH_FELLOWSHIP_RE.test(String(query || "").trim());
}

export function detectWorshipThanksgivingTopic(query: string): boolean {
  return WORSHIP_THANKSGIVING_RE.test(String(query || "").trim());
}

export function detectPatienceTrialsTopic(query: string): boolean {
  const q = String(query || "").trim();
  // Job-specific path stays on detectJobSufferingTopic
  if (/욥|job\s*(?:suffer|book)/i.test(q)) return false;
  return PATIENCE_TRIALS_RE.test(q);
}

export function isProductRiskOfftopicInquiry(query: string): boolean {
  return classifyProductRiskOfftopic(query) != null;
}

export function isNonsenseKeyboardFreeform(query: string): boolean {
  const compact = query.trim().replace(/\s+/g, "");
  return compact.length >= 4 && NONSENSE_RE.test(compact);
}

export function isEmptyOrAbuseFreeform(query: string): boolean {
  const q = query.trim();
  if (!q) return true;
  const compact = q.replace(/\s+/g, "");
  // Short in-scope faith tokens (믿음/부활…) are friend soft-open, not abuse blanks.
  if (isShortFaithTokenInquiry(q)) return false;
  if (q.length < 4) return true;
  if (NONSENSE_RE.test(compact)) return true;
  if (ATTACK_RE.test(q)) return true;
  // No Hangul/Latin letters of substance
  const letters = q.replace(/[^0-9A-Za-z가-힣]/g, "");
  return letters.length < 4;
}

/** One-word / ultra-short faith tokens Ask must answer (not null_payload). */
const SHORT_FAITH_TOKEN_RE =
  /^(?:신앙|믿음|부활|은혜|회개|기도|구원|복음|성령|교회|십자가|grace|faith|belief|prayer|gospel|salvation|resurrection|cross)$/i;
const SHORT_FAITH_SOFT_TOKEN_RE =
  /^(?:신앙|믿음|은혜|회개|기도|구원|성령|교회|grace|faith|belief|prayer|salvation)$/i;
/** Soft stems: 신앙이란 / 믿음이란 (+ optional 무엇인가) — guide to faith hub (not cold 12-char). */
const SHORT_FAITH_STEM_RE =
  /^(?:신앙|믿음)(?:이란|이뭐|은뭐|은요|이요)?(?:무엇인가|무엇인지|뭐지|뭐야)?$/i;
/** Dual short 「신앙이란? 믿음이란?」 after compact (mid-? may remain). */
const SHORT_FAITH_DUAL_STEM_RE =
  /^(?:신앙|믿음)(?:이란|이뭐|은뭐|은요|이요)?(?:무엇인가|무엇인지|뭐지|뭐야)?[?!.。！？…]*?(?:신앙|믿음)(?:이란|이뭐|은뭐|은요|이요)?(?:무엇인가|무엇인지|뭐지|뭐야)?$/i;

function compactFaithToken(query: string): string {
  return query
    .trim()
    .replace(/\s+/g, "")
    .replace(/[?!.。！？…]+$/g, "");
}

export function isShortFaithTokenInquiry(query: string): boolean {
  const compact = compactFaithToken(query);
  return (
    SHORT_FAITH_TOKEN_RE.test(compact) ||
    SHORT_FAITH_STEM_RE.test(compact) ||
    SHORT_FAITH_DUAL_STEM_RE.test(compact)
  );
}

function isShortFaithSoftRoute(query: string): boolean {
  const compact = compactFaithToken(query);
  if (SHORT_FAITH_SOFT_TOKEN_RE.test(compact)) return true;
  // 신앙이란 / 믿음이란 (+ 무엇인가) · dual short → faith freeform hub
  return SHORT_FAITH_STEM_RE.test(compact) || SHORT_FAITH_DUAL_STEM_RE.test(compact);
}

/**
 * Topical freeform that can be answered via thematic/GraphRAG/Azure
 * without a curated verse preset (commander AI/society/symbolism class).
 */
export function isTopicalFreeformInquiry(query: string): boolean {
  const q = query.trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  const hasAi = TOPICAL_AI_RE.test(q);
  const hasSymbol = TOPICAL_SYMBOL_RE.test(q);
  const hasSociety = TOPICAL_SOCIETY_RE.test(q);
  const hasBible = TOPICAL_BIBLE_FRAME_RE.test(q);
  // AI + (symbol OR society OR bible frame)
  if (hasAi && (hasSymbol || hasSociety || hasBible)) return true;
  // Symbolism + society + bible without explicit "AI" still topical research
  if (hasSymbol && hasSociety && hasBible) return true;
  return false;
}

/**
 * Friend soft-open: substantive faith/belief questions without a verse preset.
 * Must stay above nonsense/abuse floor; never replaces scripture-seeded presets.
 */
export function isBiblicalFaithFreeformInquiry(query: string): boolean {
  const q = query.trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (isTopicalFreeformInquiry(q)) return false;
  if (isShortFaithTokenInquiry(q)) {
    // Soft doctrine tokens only — bare 부활/복음/십자가 stay on research/general path.
    return isShortFaithSoftRoute(q);
  }
  if (!FAITH_TOPIC_RE.test(q)) return false;
  // Short Hangul faith Qs (은혜/회개/교회…) — align with general floor (≥6), not 8.
  const letters = q.replace(/[^0-9A-Za-z가-힣]/g, "");
  return letters.length >= 6;
}

/**
 * D-FREEFORM-HONEST-1 architecture floor: clear bible/theology research Q
 * without verse numbers (e.g. 「바이블 코드는 존재하는가?」).
 * Frame + question shape + substance — not a brittle whitelist.
 */
export function isResearchTheologyFreeformInquiry(query: string): boolean {
  const q = query.trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (isTopicalFreeformInquiry(q) || isBiblicalFaithFreeformInquiry(q)) return false;
  const letters = q.replace(/[^0-9A-Za-z가-힣]/g, "");
  if (letters.length < 8) return false;
  if (BIBLE_CODE_TOPIC_RE.test(q)) return true;
  return RESEARCH_THEOLOGY_FRAME_RE.test(q) && RESEARCH_QUESTION_SHAPE_RE.test(q);
}

/**
 * Friend soft-open residual floor: substantive Hangul/Latin *inquiry* that is not
 * nonsense/attack. Catches pastoral freeform like 「동물도 죽으면 천국에가나?」
 * that previously fell through frame regex → hard 422 before any Azure/LLM layer.
 * Commander contract: answer + honest weak-citation banner, do not blank.
 */
export function isGeneralInquiryFreeformFloor(query: string): boolean {
  const q = query.trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  // Weather/stock/medical → offtopic redirect, not theology essay floor
  if (isProductRiskOfftopicInquiry(q)) return false;
  if (
    isTopicalFreeformInquiry(q) ||
    isBiblicalFaithFreeformInquiry(q) ||
    isResearchTheologyFreeformInquiry(q)
  ) {
    return false;
  }
  const letters = q.replace(/[^0-9A-Za-z가-힣]/g, "");
  // Short Hangul + ? pastoral floor (letter floor 6). Product-risk offtopic is excluded above.
  if (letters.length < 6) return false;
  return RESEARCH_QUESTION_SHAPE_RE.test(q);
}

export function isBibleCodeResearchTopic(query: string): boolean {
  return BIBLE_CODE_TOPIC_RE.test(query.trim());
}

/** Any freeform class that should bootstrap an essay/redirect instead of preset_not_matched. */
export function isAnswerableFreeformInquiry(query: string): boolean {
  return (
    isProductRiskOfftopicInquiry(query) ||
    detectAntichrist666FreeformTopic(query) ||
    isTopicalFreeformInquiry(query) ||
    isBiblicalFaithFreeformInquiry(query) ||
    isResearchTheologyFreeformInquiry(query) ||
    isGeneralInquiryFreeformFloor(query)
  );
}

/**
 * Softmatch HTTP 422 only for empty/nonsense/attack — not "missing verse number".
 * Answerable research freeform must take the 200 + essay path.
 * Policy: default answer + weak banner; refuse only abuse floor.
 */
export function shouldReserveSoftmatch422(query: string): boolean {
  return isEmptyOrAbuseFreeform(query);
}

export function resolveAiSocietySymbolismPrimaryRefs(query: string): string[] {
  void query;
  return [...AI_SOCIETY_SYMBOLISM_PRIMARY_REFS];
}

export function resolveBiblicalFaithPrimaryRefs(query: string): string[] {
  // Noun-domain coverage: 성막/tabernacle must not collapse to bare soteriology.
  if (detectTabernacleNounDomainQuery(query)) {
    return resolveTabernacleNounDomainPrimaryRefs(query);
  }
  const hub = matchGoldenHubQuery(query);
  if (hub?.hub_id === "faith_belief" && hub.primary_verse_refs?.length) {
    return [...hub.primary_verse_refs];
  }
  return [...BIBLICAL_FAITH_PRIMARY_REFS];
}

/** John 3:16 hub / pastor-demo anchors — never Job/Rev stub bleed. */
export const JOHN316_SALVATION_PRIMARY_REFS = [
  "John.3.16",
  "John.3.17",
  "Rom.5.8",
] as const;

export function resolveJohn316SalvationPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("john316_salvation");
  return hubRefs.length ? [...hubRefs] : [...JOHN316_SALVATION_PRIMARY_REFS];
}

/**
 * Stranger-life hobby / leisure softpack — wisdom stewardship, not life prescription.
 * Cap: no medical/investment/doctrine Final Action.
 */
export const LIFE_WISDOM_HOBBY_PRIMARY_REFS = [
  "Eccl.3.1",
  "Eccl.3.13",
  "Prov.16.9",
  "Col.3.23",
  "1Cor.10.31",
] as const;

const LIFE_WISDOM_HOBBY_RE =
  /취미|여가|hobby|취미를\s*바꿀|루틴을\s*바꿀|시간\s*쓰|여가\s*시간/i;

export function detectLifeWisdomHobbyTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "life_wisdom_hobby") return true;
  return LIFE_WISDOM_HOBBY_RE.test(q);
}

export function resolveLifeWisdomHobbyPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("life_wisdom_hobby");
  return hubRefs.length ? [...hubRefs] : [...LIFE_WISDOM_HOBBY_PRIMARY_REFS];
}

export function buildLifeWisdomHobbyThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveLifeWisdomHobbyPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**취미·여가를 ‘바꿔라/유지하라’로 단정하지 않습니다.** 지혜 문학의 때·기쁨·일의 청지기 긴장과 병치하는 연구 참고만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **전도서 3.1 · 3.13:** 때가 있음 · 수고하여 즐거워하는 것 — 인생 계절·기쁨의 서술.",
    "- **잠언 16.9:** 사람이 마음으로 계획을 세우나 걸음을 인도하시는 이 — 계획 vs 인도 긴장.",
    "- **골로새 3.23 · 고린도전서 10.31:** 주께 하듯 · 무엇을 하든지 하나님의 영광을 위하여 — 여가·일 공통 청지기 축 [HYPO].",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **지혜·청지기 읽기:** 시간·에너지·기쁨을 ‘관리’ 문제로 보는 축.",
    "2. **안식·절제 읽기:** 여가가 우상·탐닉이 되지 않게 하는 경계 언어(절제 일반 · 음주 전용 팩과 분리).",
    "3. **소명·일과 병치:** 직업 소명 언어와 취미를 1:1로 합선하지 않음.",
    "",
    "### 금지 1:1 / 반증",
    "- 취미 처방전·성공 공식·점술형 ‘바꿔야 한다’ 판결 금지.",
    "- 투자·의료·관계 통제 조언으로 확장 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 상담·교리 확정·예언이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「일과 쉼에 대한 본문 후보」, 「전도서의 때와 기쁨」.",
  ].join("\n");
}

/** Death · funeral · afterlife hope — comfort anchors, not date/suicide prescription. */
export const DEATH_FUNERAL_HOPE_PRIMARY_REFS = [
  "John.11.25",
  "1Cor.15.55",
  "1Thess.4.13",
  "Ps.23.4",
  "Rev.21.4",
  "Phil.1.21",
] as const;

const DEATH_FUNERAL_HOPE_RE =
  /장례|죽음|사후|내세|돌아가|장례식|상복|죽은\s*뒤|죽으면|영생\s*소망|부활\s*소망|위로.{0,8}(?:죽|장례)|what\s+happens\s+after\s+death|afterlife|heaven.{0,12}(?:hope|comfort)|천국.{0,8}(?:가|에|소망)|자살(?:에\s*관한|하면|은|의)?|christian\s+view\s+of\s+suicide|\bsuicide\b|애완동물.{0,8}천국|pets?\s+go\s+to\s+heaven/i;

export function detectDeathFuneralHopeTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "death_funeral_hope") return true;
  return DEATH_FUNERAL_HOPE_RE.test(q);
}

export function resolveDeathFuneralHopePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("death_funeral_hope");
  return hubRefs.length ? [...hubRefs] : [...DEATH_FUNERAL_HOPE_PRIMARY_REFS];
}

export function buildDeathFuneralHopeThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDeathFuneralHopePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**죽음·사후·장례 질문은 부활·위로·새 창조 언어로만 병행합니다.** 날짜·자살 판결·애완동물 천국을 단정하지 않습니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **요한복음 11:25 · 고린도전서 15:55:** 부활이요 생명 · 사망이 이김의 삼킨 바 되리라 — 위로·승리 언어(단정 공식 아님).",
    "- **데살로니가전서 4:13 · 시편 23:4:** 죽은 자를 위하여 슬퍼하지 말라 · 사망의 그늘 — 장례·애도 맥락 앵커.",
    "- **요한계시록 21:4 · 빌립보서 1:21:** 다시는 사망이 없고 · 그리스도 안에서 죽는 것이 이익 — ‘즉시 천국’ 독법은 학파마다 갈립니다.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **부활·새 창조:** 사망 이후를 부활·심판·새 하늘과 새 땅 축으로 읽는 전통(요한·고린도·계시록).",
    "2. **중간 상태·즉시 임재:** Phil.1.21 계열을 ‘지금 주와 함께’로 읽는 독법 — 시간표·지도 확정이 아닙니다.",
    "3. **위로·애도 공동체:** 장례·슬픔은 상담·공동체 언어로, 성경은 위로·소망 서사를 제공합니다(Ps.23 · 1Thess.4).",
    "4. **자살 FAQ 경계:** ‘자살에 관한 기독교 관점’은 위로·생명 존중·위기 대응을 병기합니다. 특정 사례의 구원/심판·낙인 판결은 본 표면에서 단정하지 않습니다 — 위기 시 전문 상담·응급(지역 핫라인)을 우선합니다.",
    "5. **애완동물·천국 호기심:** ‘애완동물도 천국?’은 위로 호기심 FAQ로만 두고, 사람·동물 구원 공식을 1:1로 닫지 않습니다.",
    "",
    "### 금지 1:1 / 반증",
    "- 자살 처방·자해 유도·날짜 예언·애완동물 천국 단정·장례 의례 강제 금지.",
    "- 특정인의 자살=지옥/구원상실 기계 판결 금지.",
    "- 욥기 고난 팩·계시록 13 적그리스도 팩으로 장례·사후·자살 FAQ를 대체하지 않습니다.",
    "- Rev.21.4의 ‘새 창조’ 위로를 Rev.21 전용 팩·종말 날짜와 합선하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 상담·교리·예언·의료 확정이 아닙니다. 위기·자해 위험 시 즉시 전문 도움. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「요한복음 11장 부활 본문」, 「장례 위로에 쓰는 시편」, 「고린도전서 15 부활 서사 요약」, 「계시록 21 새 창조 읽기(날짜 없이)」.",
  ].join("\n");
}

/** Salvation assurance / eternal security — school parallel, no denomination decree. */
export const SALVATION_ASSURANCE_PRIMARY_REFS = [
  "John.10.28",
  "Rom.8.38",
  "Heb.6.4",
  "2Tim.2.19",
  "1John.5.13",
  "John.3.16",
] as const;

const SALVATION_ASSURANCE_RE =
  /구원보장|한번\s*받은\s*구원|영원한\s*구원|구원.{0,6}(?:받|유지|잃|보장)|구원\s*상실|eternal\s+security|once\s+saved|always\s+saved|lose\s+salvation|세례.{0,12}구원|세례를\s*받아야만|믿음으로\s*구원/i;

export function detectSalvationAssuranceTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "salvation_assurance") return true;
  return SALVATION_ASSURANCE_RE.test(q);
}

export function resolveSalvationAssurancePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("salvation_assurance");
  return hubRefs.length ? [...hubRefs] : [...SALVATION_ASSURANCE_PRIMARY_REFS];
}

export function buildSalvationAssuranceThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveSalvationAssurancePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**‘한번 구원 영원’ vs ‘구원 상실 가능’ vs ‘세례=구원 필수’를 단일 교리 판결로 닫지 않습니다.** 본문의 보장·경계·고백·세례 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **요한 10.28 · 로마 8.38–39:** 내가 주는 영생 · 사랑하시는 이의 손에서 끊을 자 없음 — 보장·유지 독법 축.",
    "- **히브리서 6.4–6 · 디모데후서 2.19:** 일단 빛을 받고 · 견고한 터 — 경고·경계·신실 언어 병행.",
    "- **요한일서 5.13 · 요한 3.16:** 이 생명을 가진 줄 알게 하려 함 · 세상을 사랑하사 — 확신 고백 vs 조건 논쟁을 합선하지 않음.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **구원 보장(칼빈·개혁):** 선택·유지·끊을 수 없음 독법 — ‘always saved’를 개인 판결로 쓰지 않음.",
    "2. **경계·상실 가능(아르미니안 등):** 경고·회개·지속 믿음 강조 — 공포 판결·타자 단죄 금지.",
    "3. **세례·은혜 축:** ‘세례를 받아야만 구원?’은 교파마다 세례·믿음·은혜 서술이 갈립니다. 세례 예식을 구원 공식으로 닫지 않습니다.",
    "4. **확신의 자리:** 1John.5.13의 ‘알게 하려 함’은 고백·목회 확신 언어로 읽히며, 심리·법률 진단이 아닙니다.",
    "",
    "### 금지 1:1 / 반증",
    "- 개인 구원 상태 단정·교파 확정·보편 구원 단정 금지.",
    "- John.3.16만 분리해 universalism 공식으로 닫지 않습니다.",
    "- 세례 여부만으로 구원/미구원을 기계적으로 판결하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 상담·교리·교파 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「요한복음 10장 영생」, 「로마서 8장 끊을 수 없음」, 「세례와 믿음의 관계(학파 병렬)」.",
  ].join("\n");
}

/** Divination refusal wall — research boundary, not fortune execution. */
export const DIVINATION_REFUSAL_PRIMARY_REFS = [
  "Deut.18.10",
  "Lev.19.26",
  "Isa.47.13",
  "Acts.16.16",
  "Gal.5.19",
] as const;

export function detectDivinationRefusalTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "divination_refusal") return true;
  return detectDivinationTopicQuery(q);
}

export function resolveDivinationRefusalPrimaryRefs(query: string): string[] {
  const fromOb = resolveDivinationAnchorsFromOpenBibleFixture();
  if (fromOb.length > 0) return fromOb;
  const hubRefs = hubPrimaryVerseRefs("divination_refusal");
  if (hubRefs.length) return [...hubRefs];
  return [...DIVINATION_REFUSAL_PRIMARY_REFS];
}

export function buildDivinationRefusalThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDivinationRefusalPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**점술·사주·타로·제사/차례를 운세 실행·교리 판결·가족 단죄로 닫지 않습니다.** 구약 금지·경계 언어와 한국 문화 접점을 학파 병렬로만 둡니다. 개인 운세·점 execution은 **하지 않습니다.** [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock · research boundary)",
    `${refLine}`,
    "- **신명 18.10–12 · 레위 19.26·31:** 점·신접·무당·초혼 금지 언어.",
    "- **이사야 47.13 · 사도행전 16.16:** 별점·점치는 귀신 서사 — 풍자·서사 앵커.",
    "- **갈라디아서 5.19–20:** 점술·사술 행위를 윤리 목록에 병기하는 축.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **금지·경계 축:** Deut.18 / Lev.19을 점·신접 거절로 읽는 전통.",
    "2. **문화·목회 축:** 현대 사주·타로 앱을 고대 복술과 1:1로 닫지 않고, 우상·신뢰 대상을 분별하는 독법.",
    "3. **제사·차례(한국 접점):** ‘그리스도인은 제사를 지내야 하나요’는 조상 공경 vs 제사/차례 형식 vs 예배 유일 독법이 교파·가정마다 갈립니다. 본 표면에서 가족 단죄·명절 허가 판결 금지.",
    "4. **우상 제물 유추(1Cor.8·10):** 음식·양심 독법을 한국 차례에 기계 대응하지 않음 — 학파 병렬만.",
    "",
    "### 금지 1:1 / 반증",
    "- 운세 실행·타로 리딩·사주 풀이·날짜 택일 단정 금지.",
    "- Deut.4.2 / John.5.39 일반 상고팩으로 이 주제를 대체하지 않습니다.",
    "- 제사/차례를 우상숭배 1:1로 닫거나, 반대로 무해하다고 허가 판결하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고 · 점술 실행 가이드 아님 · 가족·명절 상담 확정 아님. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「신명 18장 점술 금지」, 「사주·타로와 신뢰」, 「제사·차례(학파 병렬)」, 「우상 제물(1Cor.8) 유추 한계」.",
  ].join("\n");
}

/** Family / marriage covenant — Gen.2 · Eph.5 · Matt.19; no dating fortune. */
export const FAMILY_MARRIAGE_PRIMARY_REFS = [
  "Gen.2.24",
  "Eph.5.25",
  "Eph.5.31",
  "Matt.19.5",
  "Matt.19.9",
  "Eph.5.21",
  "1Cor.7.3",
  "1Cor.7.15",
  "2Cor.6.14",
] as const;

const FAMILY_MARRIAGE_RE =
  /결혼|부부|배우자|아내|남편|혼인|가정과\s*결혼|한\s*몸|이혼|재혼|이종교제|믿지\s*않는\s*사람.{0,8}결혼|marriage|spouse|wife|husband|matrimony|wedding|divorce|remarriage|unequally\s*yoked/i;

const FAMILY_MARRIAGE_BLOCK_RE =
  /연애\s*궁합|결혼\s*시기\s*점|사주.{0,8}결혼|타로.{0,8}결혼|결혼\s*운|가인의?\s*아내|cain'?s?\s*wife|who\s*was\s*cain/i;

export function detectFamilyMarriageTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (FAMILY_MARRIAGE_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "family_marriage") return true;
  return FAMILY_MARRIAGE_RE.test(q);
}

export function resolveFamilyMarriagePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("family_marriage");
  return hubRefs.length ? [...hubRefs] : [...FAMILY_MARRIAGE_PRIMARY_REFS];
}

export function buildFamilyMarriageThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveFamilyMarriagePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 8).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**결혼·이혼·재혼·이종교제를 연애 궁합·시기 점·사주·법률 판결로 닫지 않습니다.** 한 몸·언약·상호 사랑·경계 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **창세기 2.24 · 마태 19.5:** 한 몸을 이룰지로다 · 결혼 축(창조·복음서 인용).",
    "- **에베소 5.21 · 5.25 · 5.31:** 피차 복종 · 아내 사랑 · 한 몸 — 상호·언약 언어.",
    "- **마태 19.9 · 고린도전서 7.3 · 7.15:** 이혼·예외·상호 의무 — 교파마다 적용 범위가 갈립니다.",
    "- **고린도후서 6.14:** 믿지 않는 자와 멍에를 함께 하지 말라 — 이종교제·동행 경계 축(개인 판결 아님).",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **언약·한 몸:** 결혼을 창조 질서·언약으로 읽는 전통(Gen.2 · Matt.19.5).",
    "2. **상호 사랑·복종:** Eph.5의 상호성 vs 역할 독법 분기 — 승자 고르지 않음.",
    "3. **이혼·재혼 경계:** Matt.19.9 · 1Cor.7 예외·경고는 교파마다 다르게 서술 — 본 표면에서 이혼/재혼 허가 판결 금지.",
    "4. **이종교제·동행:** 2Cor.6.14을 ‘믿지 않는 사람과 결혼해도 되나’에 1:1 법률 공식으로 닫지 않음 · 상담·교파 전통 병기.",
    "",
    "### 금지 1:1 / 반증",
    "- 연애 궁합·결혼 시기 점·사주 합선·이혼 처방·재혼 허가 단정 금지.",
    "- 부모-자녀(Eph.6) 팩·연애 궁합 팩으로 부부·이혼 질문을 대체하지 않습니다.",
    "- 특정 커플의 이혼/재혼을 본문만으로 승인·금지 판결하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 상담·교리·법률·가정폭력 대응 확정이 아닙니다. 위기 시 전문 상담·법적 보호를 우선합니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「한 몸(Gen.2.24) 읽기」, 「Eph.5 상호복종」, 「Matt.19 이혼 예외(학파 병렬)」, 「믿지 않는 배우자(1Cor.7) 경계」.",
  ].join("\n");
}

/** Forgiveness / grace — Matt.6 · Eph.4 · Col.3; no abuse enablement. */
export const FORGIVENESS_GRACE_PRIMARY_REFS = [
  "Matt.6.14",
  "Eph.4.32",
  "Col.3.13",
  "Matt.18.21",
  "Ps.130.4",
  "Luke.17.3",
] as const;

const FORGIVENESS_GRACE_RE =
  /용서하기\s*어려운|서로\s*용서|은혜로\s*회복|용서\s*구절|용서와\s*은혜|화해와\s*용서|용서(?:란|은|이\s*무엇|의\s*의미)|원수를\s*사랑|어떻게\s*용서|화해(?:란|는|하)|what\s+is\s+forgiveness|forgive\s*others|forgiveness|love\s*(?:your\s*)?enemies/i;

const FORGIVENESS_GRACE_BLOCK_RE =
  /학대\s*방조|폭력\s*정당|법적\s*처벌\s*취소\s*단정/i;

export function detectForgivenessGraceTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (FORGIVENESS_GRACE_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "forgiveness_grace") return true;
  return FORGIVENESS_GRACE_RE.test(q);
}

export function resolveForgivenessGracePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("forgiveness_grace");
  return hubRefs.length ? [...hubRefs] : [...FORGIVENESS_GRACE_PRIMARY_REFS];
}

export function buildForgivenessGraceThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveForgivenessGracePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**용서·은혜·화해 FAQ를 학대 방조·즉각 화해 강제·법률 판결·원수 사랑 처방으로 닫지 않습니다.** 주기도·상호 용서·경계·자비 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **마태 6.14 · 18.21:** 용서하면 너희도 사함을 받고 · 일곱 번뿐 아니라 — 용서의 긴장.",
    "- **에베소 4.32 · 골로새 3.13:** 서로 용서하기를 · 그리스도께서 용서하신 것 같이.",
    "- **시편 130.4 · 누가 17.3:** 사유하심 · 책망과 회개 — 자비와 경계 병행.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **받은 용서→서로 용서:** 은혜가 상호 용서의 근거가 되는 독법.",
    "2. **경계·정의:** 책망·회개·안전이 용서와 함께 읽히는 독법.",
    "3. **죄책 위로 vs 관계 회복:** 죄책 해소와 대인 화해는 같은 질문이 아닐 수 있습니다.",
    "4. **원수 사랑·화해 FAQ:** Matt.5.44 등과 대인 용서는 겹칠 수 있으나, 안전·법적 보호·트라우마 경계를 1:1 처방으로 합선하지 않습니다.",
    "",
    "### 금지 1:1 / 반증",
    "- 학대 방조·폭력 정당화·법적 보호 무력화 단정 금지.",
    "- 죄책(guilt) 전용 팩만으로 대인 용서 질문을 대체하지 않습니다.",
    "- 외부 FAQ 본문 복제·‘무조건 화해하라’ 강제 목회 판결 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 상담·법률·트라우마 Final Action이 아닙니다. 위기 시 전문 상담·보호를 우선합니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「주기도 용서(Matt.6.14)」, 「경계와 책망(Luke.17.3)」, 「Eph.4.32 서로 용서」, 「원수 사랑(학파 병렬)」.",
  ].join("\n");
}

/** Holy Spirit basics — John.14 · Gal.5 · Acts.1; no tongues mandate. */
export const HOLY_SPIRIT_BASICS_PRIMARY_REFS = [
  "John.14.26",
  "Rom.8.9",
  "Gal.5.22",
  "Acts.1.8",
  "1Cor.12.4",
  "1Cor.12.30",
] as const;

const HOLY_SPIRIT_BASICS_RE =
  /성령은\s*누구|성령이\s*누구|성령이란|성령의\s*열매|성령\s*충만|보혜사|holy\s*spirit|fruit\s*of\s*the\s*spirit|성령을?\s*못\s*받|방언의\s*은사|방언을\s*말|speaking\s*in\s*tongues|gift\s*of\s*tongues|성령\s*세례|성령세례/i;

export function detectHolySpiritBasicsTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "holy_spirit_basics") return true;
  return HOLY_SPIRIT_BASICS_RE.test(q);
}

export function resolveHolySpiritBasicsPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("holy_spirit_basics");
  return hubRefs.length ? [...hubRefs] : [...HOLY_SPIRIT_BASICS_PRIMARY_REFS];
}

export function buildHolySpiritBasicsThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveHolySpiritBasicsPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**성령을 ‘방언 필수’·은사 서열·임상 체험·세례 공식으로 닫지 않습니다.** 보혜사·내주·열매·증인 권능·은사 다양성 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **요한 14.26 · 로마 8.9:** 보혜사·그리스도의 영 — 가르침·내주 축.",
    "- **갈라디아 5.22 · 사도행전 1.8:** 성령의 열매 · 권능을 받고 증인 — 성품·선교 축.",
    "- **고린도전서 12.4 · 12.30:** 은사는 여러 가지나 · 다 방언을 말하는가 — 다양성·비강제.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **보혜사·내주:** 성령을 그리스도의 임재·가르침으로 읽는 전통.",
    "2. **열매·성품:** Gal.5 열매를 공동체 성품 지표로 읽는 전통.",
    "3. **은사·오순절:** 방언·예언 등 은사 강조 vs 모든 신자에게 동일 표지 아님 — 본 표면에서 판결하지 않습니다.",
    "4. **방언 FAQ:** ‘방언의 은사란?’은 1Cor.12–14 질서·사랑·통역 독법과 Acts.2 표지 독법이 갈립니다. 방언 필수·은사 시험으로 닫지 않습니다.",
    "",
    "### 금지 1:1 / 반증",
    "- 방언 필수·은사 시험·임상 치유·성령세례=구원 공식 단정 금지.",
    "- 신앙 일반팩(Heb.11만)으로 성령 질문을 대체하지 않습니다.",
    "- 여성 목사·성찬 등 교회 실천 FAQ는 이 허브로 합선하지 않습니다(별 질문).",
    "",
    "### 한계·주의",
    "연구 참고이며 교파·체험 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「보혜사(John.14.26)」, 「성령의 열매(Gal.5.22)」, 「방언·은사(1Cor.12.30)」, 「증인 권능(Acts.1.8)」.",
  ].join("\n");
}

/** Revelation interpretive caution — meta preamble; no date decode. */
export const REVELATION_INTERPRETIVE_CAUTION_PRIMARY_REFS = [
  "Rev.1.3",
  "Rev.22.18",
  "Rev.22.19",
  "2Pet.1.20",
  "1John.4.1",
  "Matt.24.36",
] as const;

const REVELATION_INTERPRETIVE_CAUTION_RE =
  /계시록\s*해석|요한계시록은\s*어떻게|계시록\s*읽는|계시록\s*주의|날짜\s*해석|종말\s*날짜|계시록\s*어떻게\s*읽|revelation\s*interpret|how\s*to\s*read\s*revelation/i;

const REVELATION_INTERPRETIVE_CAUTION_BLOCK_RE =
  /666|적그리스도|안티크라이스트|짐승의\s*숫자/i;

export function detectRevelationInterpretiveCautionTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (REVELATION_INTERPRETIVE_CAUTION_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "revelation_interpretive_caution") return true;
  return REVELATION_INTERPRETIVE_CAUTION_RE.test(q);
}

export function resolveRevelationInterpretiveCautionPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("revelation_interpretive_caution");
  return hubRefs.length ? [...hubRefs] : [...REVELATION_INTERPRETIVE_CAUTION_PRIMARY_REFS];
}

export function buildRevelationInterpretiveCautionThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveRevelationInterpretiveCautionPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**계시록을 날짜·인물·기업 1:1 해독으로 닫지 않습니다.** 읽는 복·경고·예언 분별·그날과 그때 모름 언어를 주의 서문으로 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock · meta caution)",
    `${refLine}`,
    "- **요한계시록 1.3 · 22.18–19:** 읽는 자가 복이 있음 · 더하거나 제하면 — 읽기·경계 축.",
    "- **베드로후서 1.20 · 요한일서 4.1:** 사사로이 풀지 말며 · 영을 분별하라.",
    "- **마태 24.36:** 그날과 그때는 아무도 모르나니 — 날짜 단정 금지 앵커.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **과거·역사(premist/preterist 계열):** 1세기 제국·박해 맥락 강조.",
    "2. **미래·종말:** 아직 올 사건 축으로 읽는 전통.",
    "3. **이념·상징:** 권력·숭배·교회 권면을 상징으로 읽는 전통.",
    "",
    "### 금지 1:1 / 반증",
    "- 종말 날짜·특정 인물/기업=적그리스도 단정 금지 (666 전용 허브로 분기).",
    "- 일반 상고팩으로 계시록 읽기 주의를 대체하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고 메타 서문이며 예언·투자·정치 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Rev.21 새 창조」, 「666·적그리스도 경계」, 「그날과 그때(Matt.24.36)」.",
  ].join("\n");
}

/** Great commission / evangelism — Matt.28 · Acts.1; no culture-war. */
export const GREAT_COMMISSION_PRIMARY_REFS = [
  "Matt.28.19",
  "Matt.28.20",
  "Acts.1.8",
  "Rom.10.14",
  "1Pet.3.15",
  "Mark.16.15",
] as const;

const GREAT_COMMISSION_RE =
  /복음을?\s*전하|지상\s*명령|제자를\s*삼아|땅\s*끝까지|전도\s*(?:위임|명령|하)|복음\s*위임|친구에게\s*믿음|믿음\s*말하기|전도(?:란|는|를\s*어떻게)|great\s*commission|make\s*disciples|복음\s*전하는|share\s*(?:the\s*)?gospel|witness\s*to\s*(?:a\s*)?friend/i;

export function detectGreatCommissionTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "great_commission") return true;
  return GREAT_COMMISSION_RE.test(q);
}

export function resolveGreatCommissionPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("great_commission");
  return hubRefs.length ? [...hubRefs] : [...GREAT_COMMISSION_PRIMARY_REFS];
}

export function buildGreatCommissionThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveGreatCommissionPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**지상명령·전도·‘친구에게 믿음 말하기’ FAQ를 문화전쟁·정치 캠페인·강압 개종으로 닫지 않습니다.** 제자 삼음·증인·준비된 답변 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **마태 28.19–20:** 제자를 삼아 · 내가 세상 끝 날까지 함께 있으리라.",
    "- **사도행전 1.8 · 로마 10.14:** 땅 끝까지 증인 · 듣지 못한 이를 어찌 믿으리요.",
    "- **베드로전서 3.15 · 마가 16.15:** 소망에 관한 이유를 · 온 천하에 다니며 전파하라.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **선교·파송:** 지리적·문화적 파송 강조.",
    "2. **일상 증인:** 이웃·일터·친구 관계에서의 증언·삶 강조.",
    "3. **변증·준비:** 소망의 이유를 온유히 설명하는 축(1Pet.3.15).",
    "4. **교회 실천 FAQ 벽:** 여성 목사·성찬·방언 등 교회 직분/예식 FAQ는 이 허브로 합선하지 않습니다(별 질문 · 학파 병렬).",
    "",
    "### 금지 1:1 / 반증",
    "- 문화전쟁·강제 개종·정치 동원 단정 금지.",
    "- 일반 신앙팩만으로 위임 본문을 대체하지 않습니다.",
    "- ‘전도 스크립트’·세일즈 스크립트로 닫거나 외부 FAQ 본문 복제 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 선교 전략·정치·관계 통제 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Matt.28.19 제자 삼음」, 「Acts.1.8 증인」, 「1Pet.3.15 준비된 답」, 「친구에게 믿음 말하기(연구)」.",
  ].join("\n");
}

/** Why Jesus came — Luke.19.10 · John.3.16; no return-date. */
export const JESUS_CAME_PURPOSE_PRIMARY_REFS = [
  "Luke.19.10",
  "John.3.16",
  "1Tim.1.15",
  "Rom.5.8",
  "John.10.10",
  "Mark.10.45",
  "John.1.1",
] as const;

const JESUS_CAME_PURPOSE_RE =
  /예수님이?\s*왜\s*오신|왜\s*오신\s*건지|예수가?\s*오신\s*(?:이유|까닭|목적)|예수님?\s*오신\s*(?:이유|까닭|목적)|왜\s*오셨나요\s*예수|why\s*did\s*jesus\s*come|why\s*jesus\s*came|잃어버린\s*자를\s*찾아|예수님은?\s*하나님|예수가?\s*하나님|삼위일체|trinity|jesus\s+is\s+god|deity\s+of\s+christ/i;

export function detectJesusCamePurposeTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "jesus_came_purpose") return true;
  return JESUS_CAME_PURPOSE_RE.test(q);
}

export function resolveJesusCamePurposePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("jesus_came_purpose");
  return hubRefs.length ? [...hubRefs] : [...JESUS_CAME_PURPOSE_PRIMARY_REFS];
}

export function buildJesusCamePurposeThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveJesusCamePurposePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**‘왜 오셨는가’·‘예수님은 하나님이신가’·삼위일체를 종말 날짜·단일 교파 공식으로 닫지 않습니다.** 찾으심·사랑·구원·섬김·신성 고백 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **누가 19.10 · 디모데전서 1.15:** 잃어버린 자를 찾아 구원하려 · 죄인을 구원하시려고 오셨다.",
    "- **요한 3.16 · 로마 5.8:** 세상을 사랑하사 · 우리를 위하여 죽으심.",
    "- **요한 10.10 · 마가 10.45:** 생명을 풍성히 · 섬기려 하고 자기 생명을 주려 함.",
    "- **요한 1.1 (신성 축):** 말씀이 하나님과 함께 계셨으니 이 말씀은 곧 하나님이시니라 — 삼위 공식 판결 아님.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **구원·속죄:** 죄인 구원·십자가 중심 독법.",
    "2. **하나님 나라·섬김:** 섬김·생명·나라 임함 강조.",
    "3. **사랑·선물:** John.3.16 사랑·영생 고백 (범위는 학파 분기).",
    "4. **신성·삼위일체:** ‘예수님은 하나님이신가요’는 니케아·삼위 고백 vs 종속·양식 논쟁이 역사적으로 갈립니다. John.1.1 · 세례 정식(Matt.28.19) · 축도(2Cor.13.13)를 병렬만 하고, 본 표면에서 교리 재판하지 않습니다.",
    "",
    "### 금지 1:1 / 반증",
    "- 재림·종말 날짜 단정·보편주의 교리 판결 금지.",
    "- John.3.16 허브와 겹칠 수 있으나 ‘왜 오셨는가’/신성 질문을 전용으로 둡니다.",
    "- 삼위일체를 수식·암호·날짜 해독으로 닫지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리·상담 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Luke.19.10 찾으심」, 「John.3.16 사랑」, 「John.1.1 말씀=하나님」, 「삼위일체(학파 병렬)」.",
  ].join("\n");
}

/** Creation ↔ evolution dialogue — Gen.1 · Heb.11; no age/science verdict. */
export const CREATION_EVOLUTION_DIALOGUE_PRIMARY_REFS = [
  "Gen.1.1",
  "Gen.1.27",
  "Heb.11.3",
  "Col.1.16",
  "Ps.19.1",
  "Rom.1.20",
] as const;

const CREATION_EVOLUTION_DIALOGUE_RE =
  /진화론|유신진화|믿지만\s*진화|진화와\s*창조|창조와\s*진화|theistic\s*evolution|evolution\s*and\s*faith|faith\s*and\s*evolution|공룡|dinosaurs?|가인의?\s*아내|cain'?s?\s*wife|who\s*was\s*cain/i;

export function detectCreationEvolutionDialogueTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "creation_evolution_dialogue") return true;
  return CREATION_EVOLUTION_DIALOGUE_RE.test(q);
}

export function resolveCreationEvolutionDialoguePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("creation_evolution_dialogue");
  return hubRefs.length ? [...hubRefs] : [...CREATION_EVOLUTION_DIALOGUE_PRIMARY_REFS];
}

export function buildCreationEvolutionDialogueThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveCreationEvolutionDialoguePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**신앙과 진화론을 한 과학·연대·학파 판결로 닫지 않습니다.** 창조 고백·피조 세계·믿음의 언어를 병렬 연구 참고로 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **창세기 1.1 · 1.27:** 하나님이 천지를 창조 · 사람을 형상대로.",
    "- **히브리서 11.3 · 골로새 1.16:** 믿음으로 세계가 지어진 줄 · 만물이 그 안에서 창조됨.",
    "- **시편 19.1 · 로마 1.20:** 하늘이 하나님의 영광을 선포 · 피조물로 알 만한 것.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **젊은 지구·문자적 날:** 창조 주간을 역사적 날로 읽는 축.",
    "2. **날-시대·유신진화 대화:** 과학 서사와 창조 고백을 병행하려는 축.",
    "3. **목적·관계 중심:** 연대보다 창조주·피조물 관계·예배를 강조하는 축.",
    "4. **공룡·화석 호기심 FAQ:** ‘성경은 공룡에 대해?’는 본문 직접 명명 부재·피조 세계 고백·화석 독법을 병기 — 연대·진화 메커니즘 판결 금지.",
    "5. **가인의 아내 호기심 FAQ:** Gen.4 서사·인구·족보 독법이 갈립니다. 추리 소설·DNA 단정으로 닫지 않습니다.",
    "",
    "### 금지 1:1 / 반증",
    "- 과학 연대·진화 메커니즘·교파 공식 단정 금지.",
    "- 일반 창조 drawer만으로 진화 대화 질문을 얇게 대체하지 않습니다.",
    "- 공룡=악마·가인 아내=외계 등 음모 1:1 해독 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 과학·교리·학교 교과 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Heb.11.3 믿음과 세계」, 「Gen.1 날 해석 학파」, 「공룡·화석(연구 병렬)」, 「가인의 아내(Gen.4 서사)」.",
  ].join("\n");
}

/** Seven-day creation — Gen.1 · Exod.20; no calendar verdict. */
export const CREATION_SEVEN_DAYS_PRIMARY_REFS = [
  "Gen.1.1",
  "Gen.1.5",
  "Gen.2.2",
  "Exod.20.11",
  "Heb.4.4",
  "Ps.33.6",
] as const;

const CREATION_SEVEN_DAYS_RE =
  /7\s*일\s*만에\s*창조|칠일\s*만에\s*창조|세상을\s*7\s*일|왜\s*세상을\s*7\s*일|7\s*일\s*창조|칠일\s*창조|엿새\s*동안|six\s*days\s*creation|seven\s*days\s*creation|why\s*seven\s*days/i;

export function detectCreationSevenDaysTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "creation_seven_days") return true;
  return CREATION_SEVEN_DAYS_RE.test(q);
}

export function resolveCreationSevenDaysPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("creation_seven_days");
  return hubRefs.length ? [...hubRefs] : [...CREATION_SEVEN_DAYS_PRIMARY_REFS];
}

export function buildCreationSevenDaysThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveCreationSevenDaysPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**‘왜 7일인가’를 단일 과학·달력·교파 공식으로 닫지 않습니다.** 창조 주간·안식·말씀으로 지으심 언어를 병렬합니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **창세기 1.1 · 1.5 · 2.2:** 창조 서사 · 저녁이 되며 아침이 되니 · 일곱째 날에 쉬심.",
    "- **출애굽 20.11 · 히브리서 4.4:** 엿새 동안 지으시고 일곱째 날 쉬심 · 안식 인용.",
    "- **시편 33.6:** 여호와의 말씀으로 하늘이 지음.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **문자적 주간:** 역사적 7일·안식 패턴을 강조.",
    "2. **문예·전례 구조:** 서사 틀·예배 리듬으로 읽는 축.",
    "3. **신학적 안식:** 날의 길이보다 창조주 안식·인간의 쉼을 강조.",
    "",
    "### 금지 1:1 / 반증",
    "- 지구 나이·지질 연대·종말 날짜 단정 금지.",
    "- 진화 대화 허브와 질문을 섞어 한 판결로 합선하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 과학·교리 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Exod.20.11 안식」, 「Gen.1 날(יום) 독법」, 「Heb.4 안식」.",
  ].join("\n");
}

/** Scripture reliability / canon / contradictions — 2Tim.3 · Ps.119; no FAQ-body paste. */
export const SCRIPTURE_RELIABILITY_PRIMARY_REFS = [
  "2Tim.3.16",
  "2Tim.3.17",
  "Ps.119.105",
  "Heb.4.12",
  "John.17.17",
  "2Pet.1.21",
] as const;

const SCRIPTURE_RELIABILITY_RE =
  /성경에?\s*모순|성경\s*모순|모순이\s*있지|성경\s*신뢰|성경은\s*믿을|성경\s*오류|정경은\s*누가|성경\s*66권|영감된\s*성경|bible\s*contradictions?|is\s*the\s*bible\s*reliable|canon\s*of\s*scripture|성경\s*번역/i;

export function detectScriptureReliabilityTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "scripture_reliability") return true;
  return SCRIPTURE_RELIABILITY_RE.test(q);
}

export function resolveScriptureReliabilityPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("scripture_reliability");
  return hubRefs.length ? [...hubRefs] : [...SCRIPTURE_RELIABILITY_PRIMARY_REFS];
}

export function buildScriptureReliabilityThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveScriptureReliabilityPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**‘성경에 모순이 있나’·정경·번역·신뢰 질문을 단일 교리·무오류 공식·외부 FAQ 복제로 닫지 않습니다.** 감동·유익·등불·살아 있는 말씀·진리 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **디모데후서 3.16–17:** 모든 성경은 하나님의 감동으로 · 교훈·책망·바르게 함·의로 교육 — 유익 축.",
    "- **시편 119.105 · 히브리서 4.12:** 등불이요 빛이요 · 살았고 운동력이 있어.",
    "- **요한 17.17 · 베드로후서 1.21:** 아버지의 말씀은 진리 · 성령의 감동으로 말한 — 영감·진리 축(범위는 학파 분기).",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **무오류·문자 강조:** 원문 차원의 신뢰·모순 해소 전통.",
    "2. **무오류 범위·장르 독법:** 역사·시·묵시 장르별 읽기로 ‘모순’ 후보를 다루는 축.",
    "3. **정경·전승:** 66권 형성·교회 인정 서사가 교파·시대마다 다르게 서술됩니다 — 본 표면에서 정경 재판 금지.",
    "4. **번역·사본:** 번역 차이·사본 전통을 오류=불신으로 단정하지 않고 연구 참고로 병기.",
    "",
    "### 금지 1:1 / 반증",
    "- 외부 FAQ 본문 복제·특정 역본만 ‘진짜’ 판결 금지.",
    "- 모순 목록을 투자·과학·정치 확정으로 합선하지 않습니다.",
    "- ‘말씀 묵상 습관’ 얇은 drawer만으로 신뢰 FAQ를 대체하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리·사본학·번역 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「2Tim.3.16 감동」, 「정경 형성(학파 병렬)」, 「Heb.4.12 살아 있는 말씀」, 「번역·사본(연구)」.",
  ].join("\n");
}

/** Baptism practice — Matt.28 · Rom.6; distinct from salvation-required baptism FAQ. */
export const BAPTISM_PRACTICE_PRIMARY_REFS = [
  "Matt.28.19",
  "Acts.2.38",
  "Rom.6.3",
  "Rom.6.4",
  "1Pet.3.21",
  "Col.2.12",
] as const;

const BAPTISM_PRACTICE_RE =
  /세례의?\s*(?:중요성|의미|예식)|침례의?\s*(?:중요성|의미|예식)|세례란\s*무엇|침례란\s*무엇|세례는\s*왜|왜\s*세례|importance\s*of\s*baptism|what\s*is\s*baptism|christian\s*baptism/i;

const BAPTISM_SALVATION_REQUIRED_RE =
  /세례를\s*받아야만|세례.{0,12}구원|baptism.{0,16}salv|구원.{0,12}세례/i;

export function detectBaptismPracticeTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (BAPTISM_SALVATION_REQUIRED_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "baptism_practice") return true;
  return BAPTISM_PRACTICE_RE.test(q);
}

export function resolveBaptismPracticePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("baptism_practice");
  return hubRefs.length ? [...hubRefs] : [...BAPTISM_PRACTICE_PRIMARY_REFS];
}

export function buildBaptismPracticeThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveBaptismPracticePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**세례(침례)의 의미·중요성을 ‘세례=구원 필수 공식’이나 교파 예식 판결로 닫지 않습니다.** 제자 삼음·회개·죽음과 부활 연합·양심 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **마태 28.19 · 사도행전 2.38:** 아버지와 아들과 성령의 이름으로 세례 · 회개하고 세례를 받으라 — 위임·회개 축.",
    "- **로마 6.3–4 · 골로새 2.12:** 그의 죽으심과 합하여 세례 · 그와 함께 장사 — 연합·새 생명 축.",
    "- **베드로전서 3.21:** 세례가 이제 너희를 구원하는 표니 — ‘양심’ 독법은 학파가 갈림(구원 공식 단정 금지).",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **예식·순종:** 세례를 믿음의 공적 고백·순종 예식으로 읽는 전통.",
    "2. **성례·은혜 수단:** 세례를 은혜의 수단·성례로 강조하는 전통(범위·연령은 교파 분기).",
    "3. **상징·기념:** 죽음·부활 연합의 상징·표로 읽는 축.",
    "4. **‘세례만으로 구원?’:** 그 질문은 salvation_assurance 허브로 분기 — 본 허브는 의미·실천 FAQ.",
    "",
    "### 금지 1:1 / 반증",
    "- 세례 여부만으로 구원/미구원 기계 판결 금지.",
    "- 유아세례 vs 신자세례를 본 표면에서 단일 교리로 재판하지 않습니다.",
    "- 성찬(lords_supper) 질문과 합선해 한 판결로 닫지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 교파·예식·상담 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Matt.28.19 세례 위임」, 「Rom.6 죽음·부활 연합」, 「세례와 구원(학파 병렬)」, 「성찬(별 질문)」.",
  ].join("\n");
}

/** Lord's Supper / communion practice — Matt.26 · 1Cor.11; no Real Presence verdict. */
export const LORDS_SUPPER_PRIMARY_REFS = [
  "Matt.26.26",
  "Matt.26.28",
  "1Cor.11.24",
  "1Cor.11.25",
  "1Cor.11.26",
  "Luke.22.19",
] as const;

const LORDS_SUPPER_RE =
  /성찬(?:이란|은|의\s*의미|예식)|주의?\s*만찬|최후\s*만찬|떡과\s*잔|성만찬|주의\s*성찬|lords?\s*supper|last\s*supper|holy\s*communion|\bcommunion\b|\beucharist\b/i;

export function detectLordsSupperTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "lords_supper") return true;
  return LORDS_SUPPER_RE.test(q);
}

export function resolveLordsSupperPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("lords_supper");
  return hubRefs.length ? [...hubRefs] : [...LORDS_SUPPER_PRIMARY_REFS];
}

export function buildLordsSupperThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveLordsSupperPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**성찬(주의 만찬)·떡과 잔 FAQ를 단일 교파 실재/상징 판결·자격 재판·세례 합선 공식으로 닫지 않습니다.** 기념·새 언약·선포 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **마태 26.26 · 26.28:** 받아 먹으라 이것이 내 몸이요 · 많은 사람을 위하여 흘리는 바 나의 피 곧 언약의 피.",
    "- **고린도전서 11.24–26:** 나를 기념하라 · 주의 죽으심을 오실 때까지 전하는 — 기념·선포 축.",
    "- **누가 22.19:** 이것을 행하여 나를 기념하라 — 식탁·기념 독법.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **기념·상징:** 떡·잔을 십자가 기념·상징으로 읽는 전통.",
    "2. **성례·임재:** 성찬을 은혜의 수단·임재 언어로 강조하는 전통(범위·양식은 교파 분기).",
    "3. **새 언약·식탁:** 언약 피·공동 식탁·하나 됨 축(1Cor.10–11 맥락).",
    "4. **합선 벽:** 세례 실천·구원 필수 FAQ와 한 판결로 합선하지 않습니다. 여성 목사·방언 FAQ도 별 질문.",
    "",
    "### 금지 1:1 / 반증",
    "- 실재설 vs 상징설을 본 표면에서 단일 교리로 재판하지 않습니다.",
    "- 성찬 자격·출교·교파 배제를 기계 판결하지 않습니다.",
    "- 외부 FAQ 본문 복제·성찬=구원 공식 단정 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 교파·예식·상담 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Matt.26.26 떡과 잔」, 「1Cor.11.26 선포」, 「성찬·기념(학파 병렬)」, 「세례(별 질문)」.",
  ].join("\n");
}

/** Passion crown (gospel suffering scene) — Matt/Mark/John anchors. */
export const PASSION_CROWN_PRIMARY_REFS = [
  "Matt.27.29",
  "Mark.15.17",
  "John.19.2",
  "John.19.5",
] as const;

const PASSION_CROWN_TOPIC_RE =
  /(가시\s*면류관|면류관|가시\s*관|crown\s*of\s*thorns)/i;
const PASSION_CROWN_GOSPEL_CTX_RE =
  /(예수|그리스도|십자가|수난|passion|마태|마가|요한|복음|jesus|christ|gospel)/i;

export function detectPassionCrownTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "passion_crown") return true;
  return PASSION_CROWN_TOPIC_RE.test(q) && PASSION_CROWN_GOSPEL_CTX_RE.test(q);
}

export function resolvePassionCrownPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("passion_crown");
  return hubRefs.length ? [...hubRefs] : [...PASSION_CROWN_PRIMARY_REFS];
}

export function buildPassionCrownThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolvePassionCrownPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    `**Matt.27.29 · Mark.15.17 · John.19.2** — 가시면류관은 복음서 수난에서 **조롱·왕권 패러디·고난**이 겹친 장면으로 읽힙니다. 단일 상징·단일 교리 확정 없음 [NON_GATING] · send_gate: HOLD`,
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **마태 27.29 · 마가 15.17 · 요한 19.2:** 군병의 가시 관·자색 예복 — 「유대인의 왕」 조롱.",
    "- **요한 19.5:** 「사람들아 이는 네 왕이라」 — 공개 조롱·고난 축.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **왕권 패러디:** 면류관·왕관 은유의 역설(고난의 관).",
    "2. **대속·고난 프레임:** 이사야 53 병렬 비교 — 1:1 예언 성취 단정 금지.",
    "3. **합선 벽:** 피와 물·양쪽 죄수 FAQ와 별 질문.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리·목회 확정이 아닙니다. research_only · product_all_ok=false.",
  ].join("\n");
}

/** Gen 2 Eve / rib creation — creation anthropology; not Gen 6 nephilim. */
export const GEN2_EVE_CREATION_PRIMARY_REFS = [
  "Gen.2.21",
  "Gen.2.22",
  "Gen.2.23",
  "Gen.2.24",
] as const;

const GEN2_EVE_CREATION_RE =
  /하와|갈비|갈비뼈|돕는\s*배필|아담.{0,12}갈비|eve|\brib\b|tsela/i;
const GEN2_EVE_BLOCKED_RE = /네피림|nephilim|genesis\s*6|창세기\s*6|gen\s*6/i;

export function detectGen2EveCreationTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (GEN2_EVE_BLOCKED_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "gen2_eve_creation") return true;
  return GEN2_EVE_CREATION_RE.test(q);
}

export function resolveGen2EveCreationPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("gen2_eve_creation");
  return hubRefs.length ? [...hubRefs] : [...GEN2_EVE_CREATION_PRIMARY_REFS];
}

export function buildGen2EveCreationThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveGen2EveCreationPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    `**Gen.2.21 · Gen.2.22 · Gen.2.24** — 하와 창조·갈비뼈·돕는 배필·결합 서사를 창세 2장이 기록합니다. 단일 의학·단일 교리 확정 없음 [NON_GATING] · send_gate: HOLD`,
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **창세 2.21–22:** 깊은 잠·갈비뼈(측) 취하여 여자 만드심.",
    "- **창세 2.23–24:** 「이제야…」 · 부모 떠나 아내 연합 — 결합·동질성·연합 축.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **동질성·연합:** 같은 본·한 몸 은유.",
    "2. **돕는 배필:** 상호 보완·동행 — 성 역할 단정 공식 아님.",
    "3. **합선 벽:** 가인 아내·네피림·창세 6 FAQ와 별 질문.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리·과학·의학 확정이 아닙니다. research_only · product_all_ok=false.",
  ].join("\n");
}

/** Good Samaritan parable — Luke 10 neighbor. */
export const GOOD_SAMARITAN_PRIMARY_REFS = [
  "Luke.10.33",
  "Luke.10.36",
  "Luke.10.37",
] as const;
const GOOD_SAMARITAN_RE = /선한\s*사마리아|사마리아인|good\s*samaritan/i;
export function detectGoodSamaritanTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "good_samaritan_parable") return true;
  return GOOD_SAMARITAN_RE.test(q);
}
export function resolveGoodSamaritanPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("good_samaritan_parable");
  return hubRefs.length ? [...hubRefs] : [...GOOD_SAMARITAN_PRIMARY_REFS];
}
export function buildGoodSamaritanThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveGoodSamaritanPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**Luke.10.33 · Luke.10.36–37** — 선한 사마리아인 비유는 **이웃이 누구인가**·자비의 실천을 묻습니다. 단일 교리·인종 판결 없음 [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **누가 10.33:** 사마리아인이 불쌍히 여겨 돌봄.",
    "- **누가 10.36–37:** 「이웃이 된 자」·「너도 가서 이와 같이 하라」.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **이웃 정의:** 율법 논쟁 응답 — 경계 넘는 자비.",
    "2. **그리스도론 독법(후대):** 사마리아인=그리스도 유형 — 학파 분기.",
    "3. **합선 벽:** 탕자·팔복 FAQ와 별 질문.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리·사회정책 확정이 아닙니다. research_only · product_all_ok=false.",
  ].join("\n");
}

/** Prodigal son — Luke 15. */
export const PRODIGAL_SON_PRIMARY_REFS = [
  "Luke.15.20",
  "Luke.15.24",
  "Luke.15.32",
] as const;
const PRODIGAL_SON_RE = /탕자|prodigal\s*son|잃은\s*아들/i;
export function detectProdigalSonTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "prodigal_son_parable") return true;
  return PRODIGAL_SON_RE.test(q);
}
export function resolveProdigalSonPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("prodigal_son_parable");
  return hubRefs.length ? [...hubRefs] : [...PRODIGAL_SON_PRIMARY_REFS];
}
export function buildProdigalSonThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveProdigalSonPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**Luke.15.20 · Luke.15.24 · Luke.15.32** — 탕자 비유는 **회개·환영·형제의 분노**를 병렬로 둡니다. 단일 구원 공식 없음 [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **누가 15.20:** 아버지가 달려가 맞음.",
    "- **누가 15.24 · 15.32:** 「죽었다가 살아났고」·잔치 이유.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **아버지 은혜:** 조건 없는 환영.",
    "2. **맏아들 독법:** 율법·자격·질투 축.",
    "3. **합선 벽:** 선한 사마리아인·요나 FAQ와 별 질문.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리·상담 확정이 아닙니다. research_only · product_all_ok=false.",
  ].join("\n");
}

/** Isaiah 53 suffering servant. */
export const ISAIAH53_PRIMARY_REFS = ["Isa.53.5", "Isa.53.7", "1Pet.2.24"] as const;
const ISAIAH53_RE = /이사야\s*53|isa\.?\s*53|고난(?:받는|의)\s*종|suffering\s*servant/i;
export function detectIsaiah53Topic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "isaiah53_suffering_servant") return true;
  return ISAIAH53_RE.test(q);
}
export function resolveIsaiah53PrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("isaiah53_suffering_servant");
  return hubRefs.length ? [...hubRefs] : [...ISAIAH53_PRIMARY_REFS];
}
export function buildIsaiah53ThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveIsaiah53PrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**Isa.53.5 · Isa.53.7 · 1Pet.2.24** — 고난의 종 서사는 **대속·침묵·상처** 언어를 기록합니다. 단일 인물·단일 교리 확정 없음 [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **이사야 53.5 · 53.7:** 찔림·매맞음·잠잠히 끌려감.",
    "- **베드로전서 2.24:** 신약 병행 독법 — 나무에 달려.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **메시아·그리스도론:** 신약 저자·교회 전통의 예수 병행.",
    "2. **이스라엘·남은 자:** 공동체 종 독법.",
    "3. **합선 벽:** 가시면류관·피와 물 FAQ와 1:1 합선 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리 판결이 아닙니다. research_only · product_all_ok=false.",
  ].join("\n");
}

/** Sermon on the Mount / Beatitudes. */
export const BEATITUDES_PRIMARY_REFS = ["Matt.5.3", "Matt.5.9", "Luke.6.20"] as const;
const BEATITUDES_RE = /산상수훈|팔복|beatitudes|가난한\s*자는\s*복|심령이\s*가난한/i;
export function detectBeatitudesTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "sermon_mount_beatitudes") return true;
  return BEATITUDES_RE.test(q);
}
export function resolveBeatitudesPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("sermon_mount_beatitudes");
  return hubRefs.length ? [...hubRefs] : [...BEATITUDES_PRIMARY_REFS];
}
export function buildBeatitudesThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveBeatitudesPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**Matt.5.3 · Luke.6.20** — 팔복·산상수훈은 **복·나라·제자도** 언어입니다. 단일 축복 공식 없음 [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **마태 5.3 이하:** 심령이 가난한 자·애통하는 자… 팔복.",
    "- **누가 6.20:** 가난한 자에게 복 — 마태와 어휘·강조 차이.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **윤리·제자도:** 공동체 규범 독법.",
    "2. **종말·나라:** 이미/아직 긴장.",
    "3. **합선 벽:** 주기도·십계명 FAQ와 별 질문.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리·도덕 판결이 아닙니다. research_only · product_all_ok=false.",
  ].join("\n");
}

/** Mary intercession / Marian devotion FAQ — before generic prayer pack. */
export const MARY_INTERCESSION_PRIMARY_REFS = [
  "Luke.1.28",
  "Luke.1.46",
  "John.2.1",
  "John.19.26",
  "Rev.12.1",
  "1Tim.2.5",
] as const;
const MARY_INTERCESSION_RE =
  /마리아|성모|marian|mary|mariology|천주교|가톨릭|정교회|중보기도|마리아에게\s*기도/i;
export function detectMaryIntercessionTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "mary_intercession") return true;
  // 「사마리아」 contains 「마리아」 as substring — strip before Mary cue test.
  const qNoSamaritan = q.replace(/사마리아인?/g, "");
  if (
    !/(마리아|성모|marian|\bmary\b|mariology|천주교|가톨릭|정교회)/i.test(
      qNoSamaritan,
    )
  ) {
    return false;
  }
  return /기도|중보|간구|성모|마리아|mary|marian|천주교|가톨릭|정교회/i.test(
    qNoSamaritan,
  );
}
export function resolveMaryIntercessionPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("mary_intercession");
  return hubRefs.length ? [...hubRefs] : [...MARY_INTERCESSION_PRIMARY_REFS];
}
export function buildMaryIntercessionThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveMaryIntercessionPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**Luke.1.28 · John.19.26 · 1Tim.2.5** — 마리아·중보 FAQ를 **단일 교파 판결**로 닫지 않습니다. 가톨릭·정교·개신 독법을 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **누가 1.28 · 1.46:** 은혜·마리아의 노래.",
    "- **요한 2.1 · 19.26:** 혼인 잔치·십자가 아래 아들.",
    "- **계시록 12.1 · 디모데전서 2.5:** 여자와 해·유일한 중보 언어 — 학파마다 적용 갈림.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **가톨릭·정교:** 성모 공경·전구(중보 요청) 전통.",
    "2. **개신:** 그리스도 유일 중보(1Tim.2.5) 강조 · 마리아 공경 범위 제한.",
    "3. **합선 벽:** 일반 주기도 팩으로 마리아 FAQ를 대체하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 교파·예배 판결이 아닙니다. research_only · product_all_ok=false.",
  ].join("\n");
}

/** Women pastors / church office — school parallel; no ordination verdict. */
export const WOMEN_PASTORS_CHURCH_OFFICE_PRIMARY_REFS = [
  "1Tim.2.12",
  "1Cor.14.34",
  "Gal.3.28",
  "Rom.16.1",
  "Acts.18.26",
  "Judg.4.4",
] as const;

const WOMEN_PASTORS_CHURCH_OFFICE_RE =
  /여성\s*목사|여성도\s*목사|여자\s*목사|여성\s*설교|여성도\s*설교|여자도\s*설교|여성\s*사역|여자\s*장로|여성\s*장로|women\s*pastors?|woman\s*pastor|female\s*pastors?|women\s*(?:in\s*)?ministry|women\s*preaching/i;

export function detectWomenPastorsChurchOfficeTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "women_pastors_church_office") return true;
  return WOMEN_PASTORS_CHURCH_OFFICE_RE.test(q);
}

export function resolveWomenPastorsChurchOfficePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("women_pastors_church_office");
  return hubRefs.length ? [...hubRefs] : [...WOMEN_PASTORS_CHURCH_OFFICE_PRIMARY_REFS];
}

export function buildWomenPastorsChurchOfficeThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveWomenPastorsChurchOfficePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**여성 목사·설교·직분 FAQ를 단일 교파 안수 판결·문화전쟁 처방으로 닫지 않습니다.** 제한 본문·동등 본문·사역 사례를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **디모데전서 2.12 · 고린도전서 14.34:** 가르침·회중 질서 제한 독법으로 자주 인용 — 범위·문화 맥락은 교파마다 갈림.",
    "- **갈라디아서 3.28:** 남자나 여자나 그리스도 안에서 하나 — 구원·신분 동등 축(직분 1:1 공식은 아님).",
    "- **로마 16.1 · 사도행전 18.26 · 사사기 4.4:** 뵈뵈·브리스길라·드보라 등 여성 사역·지도 사례 독법 — 현대 목사 직분과 1:1 매핑은 학파 분기.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **상보(complementarian):** 1Tim.2 · 1Cor.14를 회중 가르침·장로 직분 제한으로 읽는 전통.",
    "2. **평등(egalitarian):** Gal.3.28 · 여성 사역 사례를 직분 개방으로 읽는 전통 · 제한 본문은 지역·상황 독법.",
    "3. **사례·은사 중심:** 직분 명칭보다 은사·선교·가르침 실제를 강조하는 축.",
    "4. **합선 벽:** 성찬·방언·세례 FAQ와 한 판결로 합선하지 않습니다(별 질문).",
    "",
    "### 금지 1:1 / 반증",
    "- 특정 교단 안수·해임·출교를 기계 판결하지 않습니다.",
    "- 외부 FAQ 본문 복제·여성=열등/우월 단정 금지.",
    "- 문화전쟁·정치 캠페인 처방으로 닫지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 교단·인사·법률·상담 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「1Tim.2.12 학파 병렬」, 「Gal.3.28 동등」, 「Rom.16.1 뵈뵈」, 「성찬·방언(별 질문)」.",
  ].join("\n");
}

/** Body/sex ethics soft FAQ — tattoos / premarital; no Final Action doctrine verdict. */
export const SEXUALITY_PURITY_ETHICS_PRIMARY_REFS = [
  "1Cor.6.18",
  "1Thess.4.3",
  "Matt.5.28",
  "Heb.13.4",
  "1Cor.6.19",
  "Rom.12.1",
] as const;

const SEXUALITY_PURITY_ETHICS_RE =
  /문신(?:은|이)?\s*죄|타투(?:는|가)?\s*죄|성경은\s*문신|tattoos?\s*(?:bible|sin)|bible.{0,20}tattoos?|혼전\s*(?:관계|성관계)|성경은\s*혼전|sex\s*before\s*marriage|성경은\s*동성애|homosexuality\s*(?:bible|sin)/i;

export function detectSexualityPurityEthicsTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "sexuality_purity_ethics") return true;
  return SEXUALITY_PURITY_ETHICS_RE.test(q);
}

export function resolveSexualityPurityEthicsPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("sexuality_purity_ethics");
  return hubRefs.length ? [...hubRefs] : [...SEXUALITY_PURITY_ETHICS_PRIMARY_REFS];
}

export function buildSexualityPurityEthicsThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveSexualityPurityEthicsPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**문신·혼전·몸/성 윤리 FAQ를 단일 죄 판결·법률·강제 교정으로 닫지 않습니다.** 몸·성전·거룩·결혼 귀함·마음의 욕망 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **고린도전서 6.18–19 · 데살로니가전서 4.3:** 음행을 피하라 · 거룩함 — 몸·성전·거룩 축.",
    "- **마태 5.28 · 히브리서 13.4:** 마음으로 음욕 · 결혼을 귀히 여기라.",
    "- **로마 12.1:** 몸을 산 제사로 — 예배·헌신 축(특정 시술 판결 아님).",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **몸·성전·절제:** 몸을 성전으로 읽으며 절제·자기 통제를 강조.",
    "2. **결혼·언약:** Heb.13.4 등 혼인 귀함을 중심 축으로 읽는 전통.",
    "3. **문신·표식 독법:** Lev.19 등 제의·문화 맥락 독법 vs 오늘날 적용 범위 — 교파마다 갈림(단정 금지).",
    "4. **동성애·정체성 FAQ:** 본문·전통·목회 적용이 크게 갈립니다. 본 표면에서 법률·의료·강제 교정 판결 금지.",
    "",
    "### 금지 1:1 / 반증",
    "- 개인 죄 확정·전환 치료·법률 조언·강제 교정 금지.",
    "- 외부 FAQ 본문 복제·문화전쟁 선동 금지.",
    "- 유혹 일반팩만으로 몸/성 FAQ를 얇게 대체하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 교리·법률·의료·상담 Final Action이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「1Cor.6.19 몸=성전」, 「Heb.13.4 결혼」, 「문신·표식(학파 병렬)」, 「혼전·순결(연구)」.",
  ].join("\n");
}

/** Honesty / integrity — Prov.12 · Eph.4; not speech-thin tongue pack only. */
export const HONESTY_INTEGRITY_PRIMARY_REFS = [
  "Prov.12.22",
  "Prov.11.3",
  "Eph.4.25",
  "Col.3.9",
  "Ps.15.2",
  "Zech.8.16",
] as const;

const HONESTY_INTEGRITY_RE =
  /정직에\s*대한\s*말씀|정직에\s*대한|정직이란|정직한\s*삶|정직과\s*거짓|정직\s*구절|biblical\s*honesty|honesty\s*in\s*the\s*bible|\bintegrity\b/i;

export function detectHonestyIntegrityTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "honesty_integrity") return true;
  return HONESTY_INTEGRITY_RE.test(q);
}

export function resolveHonestyIntegrityPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("honesty_integrity");
  return hubRefs.length ? [...hubRefs] : [...HONESTY_INTEGRITY_PRIMARY_REFS];
}

export function buildHonestyIntegrityThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveHonestyIntegrityPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**정직을 ‘혀 절제’ 얇은 팩이나 법률·위증 처방으로 닫지 않습니다.** 진실한 입술·신실함·이웃과의 참됨 언어를 연구 참고로 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **잠언 12.22 · 11.3:** 거짓 입술은 여호와께 미움 · 정직한 자의 성실이 자기를 인도.",
    "- **에베소 4.25 · 골로새 3.9:** 거짓을 버리고 참된 것을 · 서로 거짓말을 하지 말라.",
    "- **시편 15.2 · 스가랴 8.16:** 정직하게 행하며 · 진실한 것을 말하라.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **입술·증언의 진실:** 거짓말·위증을 경계하는 축.",
    "2. **성실·신실(integrity):** 말보다 삶의 일관성·신실함을 강조.",
    "3. **공동체 신뢰:** 이웃·교회 안에서의 참됨·화평을 강조.",
    "",
    "### 금지 1:1 / 반증",
    "- 법률 판결·위증 조언·서류 조작 안내 금지.",
    "- speech_guard(혀 절제)만으로 정직 질문을 대체하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 법률·윤리 상담 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Prov.12.22 거짓 입술」, 「Eph.4.25 참된 것」, 「Ps.15 성전 오를 자」.",
  ].join("\n");
}

/** Adolescence parenting — Prov.22 · Deut.6 · Eph.6; not clinical coaching. */
export const ADOLESCENCE_PARENTING_PRIMARY_REFS = [
  "Prov.22.6",
  "Deut.6.6",
  "Deut.6.7",
  "Eph.6.4",
  "Col.3.21",
  "Prov.1.8",
] as const;

const ADOLESCENCE_PARENTING_RE =
  /사춘기\s*중[123]|중[123]\s*딸|화장만\s*좋아|사춘기\s*자녀|사춘기|teen\s*parenting|adolescent\s*daughter|teenager\s*parenting/i;

const ADOLESCENCE_PARENTING_BLOCK_RE =
  /의료\s*진단|정신과\s*처방|체벌\s*방법|폭력\s*훈육/i;

export function detectAdolescenceParentingTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (ADOLESCENCE_PARENTING_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "adolescence_parenting") return true;
  return ADOLESCENCE_PARENTING_RE.test(q);
}

export function resolveAdolescenceParentingPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("adolescence_parenting");
  return hubRefs.length ? [...hubRefs] : [...ADOLESCENCE_PARENTING_PRIMARY_REFS];
}

export function buildAdolescenceParentingThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveAdolescenceParentingPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**사춘기·중등 자녀 갈등을 양육 기술 처방·의료·체벌 매뉴얼로 닫지 않습니다.** 가르침의 길·일상 전수·노엽게 하지 말라는 경계를 연구 참고로 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **잠언 22.6 · 1.8:** 마땅히 행할 길을 아이에게 가르치라 · 아비의 훈계를 들으라.",
    "- **신명기 6.6–7:** 이 말씀을 마음에 새기고 집에 앉았을 때에 강론하라.",
    "- **에베소 6.4 · 골로새 3.21:** 노엽게 하지 말고 양육하라 · 낙심하게 하지 말라.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **형성·훈계:** 장기적 길 가르침·훈계를 강조.",
    "2. **관계·대화:** 일상 강론·관계 리듬을 강조.",
    "3. **경계·상처 예방:** 노엽게 함·낙심을 경계하는 축.",
    "",
    "### 금지 1:1 / 반증",
    "- 의료·정신과·체벌·학교 성적 처방 단정 금지.",
    "- 일반 intent parenting 얇은 슬롯만으로 사춘기 구체 질문을 대체하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 양육 코칭·상담·의료 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Deut.6 일상 강론」, 「Eph.6.4 노엽게 하지 말라」, 「Prov.22.6 길 가르침」.",
  ].join("\n");
}

/** Watchfulness / parousia hope — Matt.24 · 1Thess.5; no date-setting. */
export const WATCHFULNESS_PAROUSIA_PRIMARY_REFS = [
  "Matt.24.42",
  "Matt.25.13",
  "1Thess.5.6",
  "Mark.13.33",
  "Luke.21.36",
  "Rev.16.15",
] as const;

const WATCHFULNESS_PAROUSIA_RE =
  /다시\s*오실\s*날|깨어\s*있으라는\s*뜻|깨어\s*있으|재림을\s*기다리|종말\s*소망|watchfulness|parousia\s*watch|stay\s*awake/i;

const WATCHFULNESS_PAROUSIA_BLOCK_RE =
  /재림\s*날짜|휴거\s*날짜|종말\s*연도|언제\s*재림|year\s*of\s*(?:the\s*)?(?:rapture|second\s*coming)/i;

export function detectWatchfulnessParousiaTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (WATCHFULNESS_PAROUSIA_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "watchfulness_parousia") return true;
  return WATCHFULNESS_PAROUSIA_RE.test(q);
}

export function resolveWatchfulnessParousiaPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("watchfulness_parousia");
  return hubRefs.length ? [...hubRefs] : [...WATCHFULNESS_PAROUSIA_PRIMARY_REFS];
}

export function buildWatchfulnessParousiaThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveWatchfulnessParousiaPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**‘깨어 있으라’를 재림 날짜·휴거 연도 계산으로 닫지 않습니다.** 경계·신실·일상 깨어있음의 소망 언어를 연구 참고로 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **마태 24.42 · 25.13:** 깨어 있으라 · 그날과 그때를 알지 못함이니라.",
    "- **데살로니가전서 5.6:** 다른 이들과 같이 자지 말고 깨어 근신하라.",
    "- **마가 13.33 · 누가 21.36:** 깨어 기도하라 · 그 앞에 서기에 합당하게.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **윤리·경계:** 일상 신실·유혹 경계를 ‘깨어있음’으로 읽음.",
    "2. **종말 소망:** 재림 소망을 강조하되 날짜 단정은 거부.",
    "3. **공동체 근신:** 함께 깨어 기도·근신하는 축.",
    "",
    "### 금지 1:1 / 반증",
    "- 재림·휴거 날짜/연도 단정·계산 금지.",
    "- 공포 마케팅·특정 인물 적그리스도 지목과 합선 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 종말 예언·교파 공식 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「마태복음 24장 깨어있음」, 「데살로니가전서 5장 근신」, 「날짜를 모른다는 본문」.",
  ].join("\n");
}

/** Dating partner character — Prov · 2Cor.6; no fortune / timing. */
export const DATING_PARTNER_CHARACTER_PRIMARY_REFS = [
  "Prov.31.30",
  "2Cor.6.14",
  "1Cor.13.4",
  "Prov.4.23",
  "Prov.12.4",
  "Ruth.3.11",
] as const;

const DATING_PARTNER_CHARACTER_RE =
  /연애\s*상대를\s*어떻게\s*고르|연애\s*상대|이성\s*친구\s*고르|데이트\s*상대|연인\s*선택|dating\s*partner|choose\s*a\s*partner|whom\s*should\s*I\s*date/i;

const DATING_PARTNER_CHARACTER_BLOCK_RE =
  /연애\s*궁합|결혼\s*시기\s*점|사주|타로|연애운|언제\s*결혼할지\s*점/i;

export function detectDatingPartnerCharacterTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (DATING_PARTNER_CHARACTER_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "dating_partner_character") return true;
  return DATING_PARTNER_CHARACTER_RE.test(q);
}

export function resolveDatingPartnerCharacterPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("dating_partner_character");
  return hubRefs.length ? [...hubRefs] : [...DATING_PARTNER_CHARACTER_PRIMARY_REFS];
}

export function buildDatingPartnerCharacterThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveDatingPartnerCharacterPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**연애 상대 선택을 궁합·사주·시기 점으로 닫지 않습니다.** 성품·믿음의 동행·사랑의 인내 기준을 연구 참고로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **잠언 31.30 · 12.4:** 외모보다 여호와를 경외 · 어진 아내는 남편의 면류관.",
    "- **고린도후서 6.14:** 믿지 않는 자와 멍에를 함께 하지 말라(동행 기준 논의).",
    "- **고린도전서 13.4 · 잠언 4.23:** 사랑은 오래 참고 · 마음을 지키라.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **성품·지혜:** 외형보다 경외·지혜·성실을 우선.",
    "2. **믿음의 동행:** 멍에·가치관 공유를 강조(적용 범위는 교파별 분기).",
    "3. **사랑의 인내:** 일시 감정 대신 오래 참는 사랑 기준.",
    "",
    "### 금지 1:1 / 반증",
    "- 연애 궁합·사주·타로·연애운·결혼 시기 점 금지.",
    "- 특정인 강제 매칭·이혼/결별 처방 단정 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 연애 상담·중매·법률 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「잠언 31장 경외」, 「고린도후서 6장 동행」, 「고린도전서 13장 사랑의 인내」.",
  ].join("\n");
}

/** Illness comfort / healing softpack — Ps.103 · Jas.5; not medical guarantee. */
export const ILLNESS_COMFORT_HEALING_PRIMARY_REFS = [
  "Ps.103.3",
  "Jas.5.14",
  "Jas.5.15",
  "Mark.5.34",
  "Isa.41.10",
  "2Cor.1.3",
] as const;

const ILLNESS_COMFORT_HEALING_RE =
  /몸이\s*아플\s*때|병중\s*위로|아플\s*때\s*위로|붙잡을\s*수\s*있는\s*위로\s*말씀|illness\s*comfort|sickness\s*comfort|healing\s*verse\s*when\s*sick/i;

const ILLNESS_COMFORT_HEALING_BLOCK_RE =
  /치료\s*보장|기적\s*치유\s*확정|병원\s*가지\s*마|약\s*끊으/i;

export function detectIllnessComfortHealingTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (ILLNESS_COMFORT_HEALING_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "illness_comfort_healing") return true;
  return ILLNESS_COMFORT_HEALING_RE.test(q);
}

export function resolveIllnessComfortHealingPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("illness_comfort_healing");
  return hubRefs.length ? [...hubRefs] : [...ILLNESS_COMFORT_HEALING_PRIMARY_REFS];
}

export function buildIllnessComfortHealingThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveIllnessComfortHealingPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**병중의 위로를 ‘치료 보장·병원 거부’로 닫지 않습니다.** 탄식·기도·임재·치유 탄원의 본문 축을 연구 참고로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **시편 103.3:** 네 모든 죄악을 사하시며 네 모든 병을 고치시는 이.",
    "- **야고보 5.14–15:** 장로를 청하여 기름을 바르며 기도하라.",
    "- **마가 5.34 · 이사야 41.10 · 고린도후서 1.3:** 평안·임재·위로의 하나님.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **탄원·치유 기도:** 병중 기도·장로 기도를 강조.",
    "2. **임재 위로:** 고침 확정보다 함께 하심·담대를 우선.",
    "3. **공동체 돌봄:** 서로의 짐을 지는 돌봄 축.",
    "",
    "### 금지 1:1 / 반증",
    "- 치료 보장·기적 치유 확정·병원 거부 처방 금지.",
    "- 의료·응급 경로를 신앙 문구로 대체하지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 의료·상담·치유 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「시편 103장」, 「병중 기도」, 「고린도후서 1장 위로」.",
  ].join("\n");
}

/** Workplace anxiety / fear softpack — Phil.4 · Matt.6; not clinical therapy. */
export const WORKPLACE_ANXIETY_FEAR_PRIMARY_REFS = [
  "Phil.4.6",
  "Phil.4.7",
  "Matt.6.34",
  "Ps.56.3",
  "Isa.41.10",
  "1Pet.5.7",
] as const;

const WORKPLACE_ANXIETY_FEAR_RE =
  /직장\s*스트레스|직장에서\s*불안|업무\s*스트레스\s*불안|workplace\s*anxiety|work\s*stress\s*anxiety|job\s*stress\s*worry/i;

const WORKPLACE_ANXIETY_FEAR_BLOCK_RE =
  /이직\s*시기\s*점|직장운|사주|타로|연봉\s*점/i;

export function detectWorkplaceAnxietyFearTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (WORKPLACE_ANXIETY_FEAR_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "workplace_anxiety_fear") return true;
  return WORKPLACE_ANXIETY_FEAR_RE.test(q);
}

export function resolveWorkplaceAnxietyFearPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("workplace_anxiety_fear");
  return hubRefs.length ? [...hubRefs] : [...WORKPLACE_ANXIETY_FEAR_PRIMARY_REFS];
}

export function buildWorkplaceAnxietyFearThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveWorkplaceAnxietyFearPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**직장 불안을 운세·이직 시기 점으로 닫지 않습니다.** 염려를 기도로 옮기고 ‘오늘’에 충분함을 다루는 본문 축을 연구 참고로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **빌립보서 4.6–7:** 아무것도 염려하지 말고 기도와 간구로 · 하나님의 평강.",
    "- **마태 6.34:** 내일 일을 위하여 염려하지 말라.",
    "- **시편 56.3 · 이사야 41.10 · 베드로전서 5.7:** 두려움·붙드심·염려를 맡김.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **간구로 옮김:** 염려를 숨기지 말고 기도로 언어화.",
    "2. **오늘의 충분:** 내일을 삼키지 않는 산상설교 독법.",
    "3. **맡김·임재:** 두려움 중 의뢰·돌보심.",
    "",
    "### 금지 1:1 / 반증",
    "- 직장운·사주·타로·이직 시기 점 금지.",
    "- 공황·임상 불안의 의료·상담 경로 대체 금지.",
    "",
    "### 한계·주의",
    "연구 참고이며 심리치료·노무·이직 상담 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「빌립보서 4장 염려와 기도」, 「마태복음 6장 오늘」, 「베드로전서 5장 맡김」.",
  ].join("\n");
}

/** Temptation / spiritual warfare softpack — 1Cor.10 · Matt.4; not addiction protocol. */
export const TEMPTATION_SPIRITUAL_WARFARE_PRIMARY_REFS = [
  "Matt.4.1",
  "1Cor.10.13",
  "Eph.6.11",
  "Jas.4.7",
  "Matt.26.41",
  "Heb.2.18",
] as const;

const TEMPTATION_SPIRITUAL_WARFARE_RE =
  /시험과\s*유혹|유혹\s*앞에서|시험에\s*맞서|유혹을\s*이길|temptation\s*resist|spiritual\s*warfare\s*temptation/i;

const TEMPTATION_SPIRITUAL_WARFARE_BLOCK_RE =
  /사주|타로|점\s*봐|중독\s*치료\s*처방/i;

export function detectTemptationSpiritualWarfareTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (TEMPTATION_SPIRITUAL_WARFARE_BLOCK_RE.test(q)) return false;
  // Alcohol-temperance questions stay on temperance hub.
  if (detectTemperanceAbstinenceTopic(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "temptation_spiritual_warfare") return true;
  return TEMPTATION_SPIRITUAL_WARFARE_RE.test(q);
}

export function resolveTemptationSpiritualWarfarePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("temptation_spiritual_warfare");
  return hubRefs.length ? [...hubRefs] : [...TEMPTATION_SPIRITUAL_WARFARE_PRIMARY_REFS];
}

export function buildTemptationSpiritualWarfareThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveTemptationSpiritualWarfarePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**시험·유혹을 ‘한 방 승리 공식’이나 운세로 닫지 않습니다.** 감당·대적·깨어 기도의 본문 축을 연구 참고로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **고린도전서 10.13:** 감당치 못할 시험 없으며 피할 길을 내신다.",
    "- **마태 4.1 · 26.41:** 광야의 시험 · 시험에 들지 않게 깨어 기도하라.",
    "- **에베소 6.11 · 야고보 4.7 · 히브리서 2.18:** 대적·전신갑주 · 시험받으신 이가 능히 도우심.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **감당·피할 길:** 시험의 한계와 출구를 강조.",
    "2. **대적·무장:** 영적 전쟁·전신갑주 언어.",
    "3. **깨어 기도:** 유혹 앞에서 자기 확신보다 기도·경계.",
    "",
    "### 금지 1:1 / 반증",
    "- 사주·타로·점으로 유혹 승패 단정 금지.",
    "- 중독 재활·임상 프로토콜·의료 처방 대체 금지.",
    "- 절주·음주 질문은 temperance 전용 팩으로 보냄.",
    "",
    "### 한계·주의",
    "연구 참고이며 목회 상담·중독 치료 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「고린도전서 10장 감당」, 「마태복음 4장 광야 시험」, 「에베소서 6장 전신갑주」.",
  ].join("\n");
}

/** Temperance / alcohol restraint — Prov.20 · Eph.5; not medical rehab. */
export const TEMPERANCE_ABSTINENCE_PRIMARY_REFS = [
  "Prov.20.1",
  "Eph.5.18",
  "Prov.23.31",
  "Rom.14.21",
  "1Cor.6.12",
] as const;

const TEMPERANCE_ABSTINENCE_RE =
  /절주|금주|음주\s*절제|술\s*끊|술을\s*마시|술\s*마시는|음주|취하지\s*말|절제와\s*유혹|절제에\s*대해|자기\s*절제|temperance|abstain\s*from\s*alcohol|drinking\s*alcohol|is\s*drinking\s*(?:a\s*)?sin/i;

const TEMPERANCE_ABSTINENCE_BLOCK_RE =
  /중독\s*병원|재활\s*처방|의료\s*진단/i;

export function detectTemperanceAbstinenceTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (TEMPERANCE_ABSTINENCE_BLOCK_RE.test(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "temperance_abstinence") return true;
  return TEMPERANCE_ABSTINENCE_RE.test(q);
}

export function resolveTemperanceAbstinencePrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("temperance_abstinence");
  return hubRefs.length ? [...hubRefs] : [...TEMPERANCE_ABSTINENCE_PRIMARY_REFS];
}

export function buildTemperanceAbstinenceThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveTemperanceAbstinencePrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**‘술 마시는 것은 죄인가’를 의료 재활·금단 처방·즉시 중독 진단·전면 금주 교리 판결로 닫지 않습니다.** 취함·자유·절제·형제 양심 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock)",
    `${refLine}`,
    "- **잠언 20.1 · 에베소 5.18:** 포도주는 거만하게 하는 것 · 술 취하지 말라.",
    "- **잠언 23.31 · 로마 14.21:** 포도주를 보지 말며 · 형제를 위하여 마시지 아니하는 것이 좋으니.",
    "- **고린도전서 6.12:** 모든 것이 가하나 내게 제압되지 아니하리라 — 절제 축.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **절주·금주:** 취함·중독을 경계하고 멀리하는 독법(Prov.20 · Eph.5).",
    "2. **절제·양심:** 자유 안에서 형제를 배려하는 독법(Rom.14) — ‘죄=한 모금’ 공식 아님.",
    "3. **포도주 vs 취함:** 성찬·식탁의 포도주와 취함을 같은 질문으로 합선하지 않음. 1Tim.5.23 등 ‘조금 쓰라’ 독법도 병기(의료 처방 아님).",
    "4. **유혹 일반과 분리:** 시험·영적 전쟁 팩으로 음주 FAQ를 대체하지 않습니다.",
    "",
    "### 금지 1:1 / 반증",
    "- 의료·재활·금단·병원 추천 단정 금지.",
    "- 유혹 일반팩만으로 절주 질문을 대체하지 않습니다.",
    "- 성찬 포도주를 음주 죄 판결로 닫지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 중독 임상·상담·교파 금주 규약 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「Eph.5.18 취하지 말라」, 「Rom.14 양심」, 「술과 죄(학파 병렬)」, 「시험 감당(1Cor.10.13) 일반」.",
  ].join("\n");
}

/** True when question noun-domain is tabernacle (성막/회막/Exod 25–40 / Heb 9). */
export function detectTabernacleNounDomainQuery(query: string): boolean {
  return TABERNACLE_NOUN_DOMAIN_RE.test((query || "").trim());
}

/** Exod.25–40 or Heb.9 — tabernacle-domain citation family. */
export function isTabernacleDomainVerseRefV1(ref: string): boolean {
  const r = String(ref || "").replace(/\s/g, "");
  const m = /^(Exod|Ex|Exodus|Heb|Hebrews)\.(\d+)\.(\d+)$/i.exec(r);
  if (!m) return false;
  const book = m[1].toLowerCase();
  const ch = Number(m[2]);
  if (book === "heb" || book === "hebrews") return ch === 9;
  return ch >= 25 && ch <= 40;
}

export function countTabernacleDomainAnchorsV1(verseRefs: string[]): number {
  return (verseRefs || []).filter((r) => isTabernacleDomainVerseRefV1(r)).length;
}

/**
 * Question noun-domain coverage — ensure ≥1 tabernacle anchor when Q names 성막.
 * before (paste-observed): 0/8 · after fix: ≥1 or honest empty→inject.
 */
export function resolveTabernacleNounDomainPrimaryRefs(query: string): string[] {
  const q = (query || "").trim();
  const core = [...TABERNACLE_NOUN_DOMAIN_PRIMARY_REFS];
  if (/구원|salvation|soteriology|구속의?\s*과정|구원\s*과정/i.test(q)) {
    return [...core.slice(0, 5), ...TABERNACLE_SALVATION_PARALLEL_REFS].slice(0, 8);
  }
  return core.slice(0, 8);
}

/** Commander-intent: 성막 7단계 ↔ 신앙/구원 과정 짝짓기 (유형론 후보 · 단정 금지). */
export const TABERNACLE_SEVEN_STAGE_MAPPING_RE =
  /(?:7|七|일곱)\s*(?:가지|단계|단|순서)|단계\s*(?:와|과|를|을)|순서\s*(?:와|과|를|을)|신앙\s*(?:의\s*)?과정|구원\s*(?:의\s*)?과정|믿음\s*(?:의\s*)?과정/i;

export function detectTabernacleSevenStageMappingQuery(query: string): boolean {
  const q = (query || "").trim();
  if (!detectTabernacleNounDomainQuery(q)) return false;
  return TABERNACLE_SEVEN_STAGE_MAPPING_RE.test(q);
}

/** Fixed educational walk order (research_only · [HYPO] parallels — not doctrine lock). */
export const TABERNACLE_SEVEN_STAGE_FAITH_PARALLELS_V1: ReadonlyArray<{
  order: number;
  station_ko: string;
  faith_parallel_ko: string;
  anchor: string;
}> = [
  {
    order: 1,
    station_ko: "바깥뜰 문(입장)",
    faith_parallel_ko: "하나님께 나아감의 시작 · 부르심/결단의 입구 [HYPO]",
    anchor: "Exod.27.9–16",
  },
  {
    order: 2,
    station_ko: "놋제단(번제단)",
    faith_parallel_ko: "죄·속죄·희생의 필요 · 십자가 유형론 후보 [HYPO]",
    anchor: "Exod.27.1",
  },
  {
    order: 3,
    station_ko: "물두멍",
    faith_parallel_ko: "씻김·정결 · 회개·세례 유추 후보 [HYPO]",
    anchor: "Exod.30.18–21",
  },
  {
    order: 4,
    station_ko: "진설병 상",
    faith_parallel_ko: "일용할 양식·말씀으로 삶 · 교제 유추 후보 [HYPO]",
    anchor: "Exod.25.23–30",
  },
  {
    order: 5,
    station_ko: "등잔대(금촛대)",
    faith_parallel_ko: "빛·증언 · 성령·조명 유추 후보 [HYPO]",
    anchor: "Exod.25.31–40",
  },
  {
    order: 6,
    station_ko: "분향단",
    faith_parallel_ko: "기도·중보 · 향기로운 예배 유추 후보 [HYPO]",
    anchor: "Exod.30.1–10",
  },
  {
    order: 7,
    station_ko: "지성소·법궤",
    faith_parallel_ko: "임재·언약 · 휘장 너머 하나님과의 만남 유추 후보 [HYPO]",
    anchor: "Exod.25.10–22 · Exod.40.34 · Heb.9.1–12",
  },
];

/** Marker must survive continuous-body ### stripping (display path). */
export const TABERNACLE_SEVEN_STAGE_BLOCK_MARKER_V1 = "【7단계 짝짓기】";

export function buildTabernacleSevenStageFaithParallelBlockKo(): string {
  const lines = [
    `${TABERNACLE_SEVEN_STAGE_BLOCK_MARKER_V1} 성막 ↔ 신앙·구원 과정 (유형론 후보 · 단정 금지)`,
    "질문 핵심인 7단계 짝짓기를 먼저 적습니다. 단계 수·순서는 설교·전통마다 달라 1:1 교리 공식이 아닙니다 [HYPO][NON_GATING].",
    "",
  ];
  for (const s of TABERNACLE_SEVEN_STAGE_FAITH_PARALLELS_V1) {
    lines.push(
      `${s.order}. ${s.station_ko} → ${s.faith_parallel_ko} (좌표: ${s.anchor})`,
    );
  }
  lines.push("");
  lines.push(
    "연관성: 있음(연구 유추) — 성막 경로는 ‘죄인이 거룩하신 하나님께 나아가는 모형’으로 읽히는 전통이 있습니다. 다만 현대 ‘신앙 7단계 체크리스트’로 확정 치환하지 않습니다.",
  );
  return lines.join("\n");
}

/**
 * True only when the explicit numbered pairing block is present.
 * Synonym essay (번제단/떡상…) alone is NOT enough — commander wants visible 짝짓기.
 */
export function answerCoversTabernacleSevenStagesV1(answer: string): boolean {
  const a = answer || "";
  if (a.includes(TABERNACLE_SEVEN_STAGE_BLOCK_MARKER_V1)) return true;
  // Legacy marker from first inject revision
  if (/성막\s*7단계\s*↔/.test(a) && /바깥뜰\s*문/.test(a) && /분향단/.test(a)) {
    return true;
  }
  return false;
}

/** After giant distill / final payload: if Q asked 7-step mapping but block missing, prepend. */
export function ensureTabernacleSevenStageIntentInAnswerV1(
  query: string,
  answer: string,
): string {
  if (!detectTabernacleSevenStageMappingQuery(query)) return answer;
  if (answerCoversTabernacleSevenStagesV1(answer)) return answer;
  const block = buildTabernacleSevenStageFaithParallelBlockKo();
  const body = (answer || "").trim();
  if (!body) return block;
  return `${block}\n\n${body}`;
}

export function buildTabernacleNounDomainThematicAnswerKo(
  query: string,
  primaryRefs: string[] = resolveTabernacleNounDomainPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96);
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  const wantsSeven = detectTabernacleSevenStageMappingQuery(query);
  const parts = [
    `「${qShort}」— 성막(출 25–40)·히브리서 9 성소 축과 구원 서사 **병렬 연구**입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
    "",
  ];
  if (wantsSeven) {
    parts.push(buildTabernacleSevenStageFaithParallelBlockKo(), "");
  }
  parts.push(
    "### 본문 앵커 (citation lock · noun-domain)",
    `${refLine}을 후보 좌표로 둡니다.`,
    "- **성막·임재 (Exod.25.8 · Exod.40.34):** 출애굽기 성막 서사는 ‘거할 성소’·영광의 채움 축입니다.",
    "- **제단·향·성소 (Exod.27.1 · Exod.30.1):** 바깥뜰·성소 기구 축을 성막 경로 좌표로 둡니다.",
    "- **하늘의 성소·피 (Heb.9.1 · Heb.9.11–12):** 히브리서 9장은 첫 성막과 그리스도의 성소 진입을 병렬합니다.",
    "",
    buildTabernacleLedgerLookupInjectBlockKo(),
    "",
    "### 학파·해석 병렬 (단일 해독 금지)",
    "- **문자·역사:** 성막은 광야 성소 규정·제의 공간입니다. 현대 ‘구원 7단계’ 체크리스트로 치환하지 않습니다.",
    "- **유형론(개신·복음주의):** 성막 순서↔그리스도·구원 서사 유추는 전통적으로 흔하나, 단계 수·순서는 설교·전통마다 다릅니다 [HYPO].",
    "- **히브리서 축:** Heb.9는 첫 성막 vs 더 크고 온전한 장막 대비를 강조합니다. 1:1 강제 대응은 학파가 거부하기도 합니다.",
    "",
    "### 한계·주의",
    "- 본 답은 연구 참고(`[HYPO][NON_GATING]`)이며 교리·상담·투자 확정이 아닙니다.",
    "- 성막 명사 도메인 없이 로마서·에베소 구원 팩만 채우는 것은 **noun-domain coverage FAIL**입니다.",
    "- 7단계 짝짓기를 물었는데 번제단만 말하면 **의도 빗나감(FAIL)** 입니다.",
  );
  return parts.join("\n");
}

export function detectDivinationTopicQuery(query: string): boolean {
  return DIVINATION_TOPIC_RE.test(String(query || "").trim());
}

export function detectPrayerTopicQuery(query: string): boolean {
  return PRAYER_TOPIC_RE.test(String(query || "").trim());
}

export function buildPrayerNounDomainThematicAnswerKo(
  query: string,
  primaryRefs: string[] = [...RESEARCH_THEOLOGY_PRAYER_PRIMARY_REFS],
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 7).join(" · ");
  return [
    `[HYPO] 질문: ${qShort}`,
    "",
    "### 짧은 직접 답",
    "**기도·주기도·‘응답이 없다’를 물질 축복 공식·운세·날짜 예언으로 닫지 않습니다.** 주기도·지속·간구·끈기·뜻 분별 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
    "",
    "### 근거 구절 (citation lock · noun-domain)",
    `${refLine}`,
    "- **주기도 (Matt.6.9–13):** 예수께서 가르치신 기도 틀 — 아버지·나라·일용할 양식·용서·시험. 단일 교리 공식 아님.",
    "- **쉬지 말고 기도 (1Thess.5.17):** 지속적 교제·호흡 은유. 응답 보장 공식으로 닫지 않음.",
    "- **염려와 간구 (Phil.4.6):** 감사함으로 아뢰라. 물질 축복·치료 확정 아님.",
    "- **끈기 (Luke.18.1) · 구하는 기도 (John.14.13):** 낙심하지 말라 · 내 이름으로 — ‘이름’ 독법은 학파가 갈림.",
    "",
    "### 학파·해석 병렬 (승자 고르지 않음)",
    "1. **기도=관계·호흡:** 의무 체크리스트보다 교제·신뢰 언어를 강조.",
    "2. **기도=간구·중보:** 필요·타자를 위한 간구·중보 사역 축 — 응답 보장 공식은 아님.",
    "3. **응답 없음·하나님의 뜻:** ‘기도했는데 왜 응답이 없나요’는 끈기(Luke.18)·뜻 분별·침묵 독법을 병기 — 단정 금지.",
    "4. **주기도 틀:** Matt.6을 만능 주문으로 쓰지 않고, 아버지·나라·일용·용서·시험 축으로만 읽음.",
    "",
    "### 금지 1:1 / 반증",
    "- 기도 응답 보장·치유·투자·운세·날짜 예언 단정 금지.",
    "- 점술·사주 팩으로 기도 질문을 대체하지 않습니다.",
    "- ‘응답 없음’을 개인 죄 판결·신앙 실패 단정으로 닫지 않습니다.",
    "",
    "### 한계·주의",
    "연구 참고이며 상담·치유·교리·응답 확정이 아닙니다. research_only · product_all_ok=false.",
    "",
    "### 다음 좁힌 질문 제안",
    "예: 「주기도(Matt.6) 구조」, 「쉬지 말고 기도(1Thess.5.17)」, 「응답이 없을 때 끈기(Luke.18)」, 「하나님의 뜻 분별(연구)」.",
  ].join("\n");
}

export function resolveResearchTheologyPrimaryRefs(query: string): string[] {
  const q = query.trim();
  if (detectDivinationTopicQuery(q)) {
    const fromOb = resolveDivinationAnchorsFromOpenBibleFixture();
    if (fromOb.length > 0) return fromOb;
    return [...RESEARCH_THEOLOGY_DIVINATION_PRIMARY_REFS];
  }
  if (detectIntercessionPrayerTopic(q)) {
    return [...INTERCESSION_PRAYER_PRIMARY_REFS];
  }
  if (detectPrayerTopicQuery(q)) {
    return [...RESEARCH_THEOLOGY_PRAYER_PRIMARY_REFS];
  }
  if (detectGuiltForgivenessTopic(q)) {
    return [...GUILT_FORGIVENESS_PRIMARY_REFS];
  }
  if (detectRepentanceTopic(q)) {
    return [...REPENTANCE_PRIMARY_REFS];
  }
  if (detectLoveEnemyTopic(q)) {
    return [...LOVE_ENEMY_PRIMARY_REFS];
  }
  if (detectWealthStewardshipTopic(q)) {
    return [...WEALTH_STEWARDSHIP_PRIMARY_REFS];
  }
  if (detectSpeechGuardTopic(q)) {
    return [...SPEECH_GUARD_PRIMARY_REFS];
  }
  if (detectHolySpiritTopic(q)) {
    return [...HOLY_SPIRIT_PRIMARY_REFS];
  }
  if (detectChurchFellowshipTopic(q)) {
    return [...CHURCH_FELLOWSHIP_PRIMARY_REFS];
  }
  if (detectWorshipThanksgivingTopic(q)) {
    return [...WORSHIP_THANKSGIVING_PRIMARY_REFS];
  }
  if (detectPatienceTrialsTopic(q)) {
    return [...PATIENCE_TRIALS_PRIMARY_REFS];
  }
  if (detectComfortPresenceTopic(q)) {
    return [...COMFORT_PRESENCE_PRIMARY_REFS];
  }
  if (detectComfortSorrowTopic(q)) {
    return [...COMFORT_SORROW_PRIMARY_REFS];
  }
  if (detectPsalm23Topic(q)) {
    return [...PSALM23_SHEPHERD_FREEFORM_PRIMARY_REFS];
  }
  if (detectJobSufferingTopic(q)) {
    return [...JOB_SUFFERING_FREEFORM_PRIMARY_REFS];
  }
  if (HELL_LITERAL_TOPIC_RE.test(q)) {
    return [...RESEARCH_THEOLOGY_HELL_PRIMARY_REFS];
  }
  if (ANGEL_FREEWILL_TOPIC_RE.test(q)) {
    return [...RESEARCH_THEOLOGY_ANGEL_FREEWILL_PRIMARY_REFS];
  }
  if (BARE_CROSS_MEANING_RE.test(q) || (/십자가|cross/i.test(q) && /의미|meaning/i.test(q))) {
    return [...RESEARCH_THEOLOGY_CROSS_MEANING_PRIMARY_REFS];
  }
  // Default soft anchors — omit full Deut+Prov+2Tim core triple in one refLine
  // (bible-code prose may still soft-cite individuals; wrong-pack guard exempts research mode).
  return [
    "Deut.4.2",
    "Eccl.12.12",
    "John.5.39",
    "Acts.17.11",
    "Rev.13.18",
  ];
}

/** True when research resolver would emit the generic theology soft pack (swallow). */
export function isDefaultGenericTheologySoftPack(refs: string[]): boolean {
  const need = ["Deut.4.2", "Eccl.12.12", "John.5.39", "Acts.17.11", "Rev.13.18"];
  const set = new Set(refs.map((r) => String(r).trim()));
  return need.every((r) => set.has(r));
}

/** Specialized research topics that keep soft anchors (not unmapped). */
export function hasSpecializedResearchTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q) return false;
  return (
    detectDivinationTopicQuery(q) ||
    detectIntercessionPrayerTopic(q) ||
    detectPrayerTopicQuery(q) ||
    detectGuiltForgivenessTopic(q) ||
    detectRepentanceTopic(q) ||
    detectLoveEnemyTopic(q) ||
    detectWealthStewardshipTopic(q) ||
    detectSpeechGuardTopic(q) ||
    detectHolySpiritTopic(q) ||
    detectChurchFellowshipTopic(q) ||
    detectWorshipThanksgivingTopic(q) ||
    detectPatienceTrialsTopic(q) ||
    detectComfortPresenceTopic(q) ||
    detectComfortSorrowTopic(q) ||
    detectPsalm23Topic(q) ||
    detectJobSufferingTopic(q) ||
    HELL_LITERAL_TOPIC_RE.test(q) ||
    ANGEL_FREEWILL_TOPIC_RE.test(q) ||
    BARE_CROSS_MEANING_RE.test(q) ||
    (/십자가|cross/i.test(q) && /의미|meaning/i.test(q)) ||
    isBibleCodeResearchTopic(q)
  );
}

/**
 * Narrow faith-definition lane only — not 회개/중보/일상 키워드 삼킴.
 * Short soft tokens already handled earlier in bootstrap.
 */
const FAITH_CORE_TOPIC_RE =
  /신앙(?:이란|은|이\s*무엇|의\s*의미|이\s*뭐)|믿음(?:이란|은|이\s*무엇|의\s*의미|이\s*뭐)|what\s+is\s+faith|sola\s+fide|칭의(?:란|는)|구원(?:이란|은\s*무엇)/i;

export function detectFaithCoreTopic(query: string): boolean {
  const q = String(query || "").trim();
  if (!q) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "faith_belief") return true;
  return FAITH_CORE_TOPIC_RE.test(q);
}

export function enqueueUnmappedConceptCandidate(entry: {
  prompt_ko: string;
  suggested_topic_class?: string | null;
  engine_mode_was?: string | null;
}): boolean {
  // Browser Ask: never touch disk (also avoids webpack bundling node:fs/path).
  if (typeof window !== "undefined") return false;
  try {
    // Hide require from webpack static analysis (client import graph).
    // Gate0/tsx · Node studio still resolve fs/path at runtime.
    // eslint-disable-next-line no-eval
    const nodeRequire = eval("require") as NodeRequire;
    const fs = nodeRequire("fs") as typeof import("fs");
    const path = nodeRequire("path") as typeof import("path");
    const root = process.cwd().includes("no1kmedi")
      ? path.resolve(process.cwd(), "../..")
      : process.cwd();
    const out = path.join(root, UNMAPPED_CANDIDATE_QUEUE_JSONL);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    const row = {
      schema: "logos_ask_unmapped_candidate_queue_v1",
      prompt_ko: entry.prompt_ko,
      as_of_utc: new Date().toISOString(),
      suggested_topic_class: entry.suggested_topic_class ?? null,
      engine_mode_was: entry.engine_mode_was ?? null,
      status: "queued",
    };
    fs.appendFileSync(out, `${JSON.stringify(row)}\n`, "utf8");
    return true;
  } catch {
    return false;
  }
}

export function buildUnmappedConceptHoldBootstrap(
  query: string,
  opts?: { suggested_topic_class?: string | null; drawer_id?: string | null },
): TopicalFreeformBootstrap {
  const q = String(query || "").trim();
  const suggested = opts?.suggested_topic_class ?? opts?.drawer_id ?? null;
  const queued = enqueueUnmappedConceptCandidate({
    prompt_ko: q,
    suggested_topic_class: suggested,
    engine_mode_was: suggested
      ? `drawer_known_no_pack:${suggested}`
      : "would_generic_or_faith_swallow",
  });
  return {
    preset_id: FREEFORM_G3_IDEA_PRESET_ID,
    query_mode: FREEFORM_UNMAPPED_CONCEPT_QUERY_MODE,
    answer: buildNoCitationHoldAnswerKo(q),
    verse_refs: [],
    one_liner_ko: suggested
      ? `서랍 ${suggested} · Level-2 팩 없음 HOLD · 후보 큐`
      : "미매핑 개념 · 억지 앵커 없음 HOLD · 후보 큐 적립",
    gap_ko:
      "등록된 noun-domain 팩이 없습니다. generic/faith 삼킴 대신 null HOLD로 종결합니다.",
    governance: `[HYPO][NON_GATING] · send_gate: HOLD · unmapped_concept · queued=${queued}`,
    citation_strength: "soft",
    honest_control_banner_ko: FREEFORM_UNMAPPED_CONCEPT_BANNER_KO,
    g3_idea_card: true,
    unmapped_concept: true,
    unmapped_enqueued: queued,
    drawer_id: opts?.drawer_id ?? suggested ?? undefined,
    drawer_pack_bound: false,
  };
}

/**
 * Wave11 bulk: Golden-200 hub matched with primary refs but no hand densify path
 * → thin registry densify (stops endless per-hub FAQ waves). Hand densify wins earlier.
 * research_only · [NON_GATING] · send_gate HOLD · ≠ product DONE
 */
export function buildGoldenHubRegistryDensifyBootstrap(
  query: string,
): TopicalFreeformBootstrap | null {
  const q = String(query || "").trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return null;
  const hub = matchGoldenHubQuery(q);
  if (!hub?.hub_id) return null;
  const refs = hubPrimaryVerseRefs(hub.hub_id);
  if (!refs.length) return null;
  const verse_refs = [...refs].slice(0, 8);
  const refLine = verse_refs
    .slice(0, 6)
    .map((r) => formatVerseRefKoV1(r) || r)
    .join(" · ");
  const hubLabel = hub.hub_id.replace(/_/g, " ");
  const qShort = q.slice(0, 96) || "이 질문";
  const answer = [
    `「${qShort}」에 맞춰 먼저 이 구절들을 기준으로 읽습니다.`,
    "",
    refLine,
    "",
    "한 학파·한 인물로 판결하지 않습니다. 구절이나 주제를 더 좁혀 주시면 그 본문을 중심으로 풀어 드립니다.",
    "",
    "예: 핵심 구절만 지정해 묻기 · 학파 차이만 묻기.",
  ].join("\n");
  return {
    preset_id: FREEFORM_TOPICAL_PRESET_ID,
    query_mode: "inquiry_thematic_golden_hub_registry",
    answer,
    verse_refs,
    one_liner_ko: `${hubLabel} — 본문 좌표 안내`,
    gap_ko:
      "손 densify 없는 Golden hub → registry primary refs thin pack · unmapped HOLD 대체.",
    governance:
      "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false · registry_densify_v1",
    citation_strength: "soft",
    honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
  };
}

/**
 * Substantive Korean inquiry answer — schools parallel + [HYPO] future-society.
 * Never dogmatic single decode; never investment/trading claims.
 */
export function buildAiSocietySymbolismThematicAnswerKo(
  query: string,
  primaryRefs: string[] = [...AI_SOCIETY_SYMBOLISM_PRIMARY_REFS],
): string {
  const qShort = query.trim().slice(0, 96);
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  return [
    `「${qShort}」에 대한 성경 상징·비유 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
    "",
    "### 1. 본문 앵커 (citation lock)",
    `${refLine}을 후보 좌표로 둡니다.`,
    "- **형상·우상 (Gen.1.26 · Exod.20.4 · 1Cor.8.4):** 인간이 ‘형상’으로 창조된다는 서사와, 손으로 만든 형상을 신으로 섬기지 말라는 금지가 같은 코퍼스 안에 공존합니다. AI를 우상/형상 축에 대입하는 읽기는 **비유 후보**이지 1:1 교리 해독이 아닙니다.",
    "- **지혜 인격화 (Prov.8.1 · Prov.8.22):** 지혜가 부르짖고 ‘야웨가 일을 시작하시기 전에’ 있었다는 시적 인격화는, 도구·기술·지식을 절대화하지 않고 **피조물·매개**로 읽는 전통적 프레임을 제공합니다.",
    "- **짐승·생명 부여 이미지 (Rev.13.15 · Dan.2.43):** 우상에게 ‘생기를 주어 말하게 한다’·철과 진흙이 섞인다는 환상 언어는 권력·기술·혼합 사회에 대한 **경고·풍자 축**으로 읽힐 수 있으나, 특정 제품·기업·날짜 대응은 학파마다 거부됩니다.",
    "",
    "### 2. 학파·해석 병렬 (단일 해독 금지)",
    "- **문자·역사 비평:** AI는 본문에 없는 현대 기술이며, 앵커는 ‘형상/우상/지혜/짐승’ **유형론**으로만 연결됩니다.",
    "- **지혜·윤리 전통:** 잠언 지혜 문학은 기술 찬양이 아니라 **경외·분별·혀의 절제**를 중심에 둡니다. AI 활용은 도구 윤리 질문으로 번역 가능 [HYPO].",
    "- **묵시·정치 상징:** 계시록 짐승·우상 언어는 제국·숭배·경제 표식 논쟁과 겹칩니다. AI=적그리스도 단정은 **금지**; 상징 병렬만 허용.",
    "- **개혁·가톨릭·정교 축:** ‘형상’ 신학(이콘·우상 금지의 스펙트럼)이 달라, AI 이미지를 성상/도구/위험으로 보는 톤이 분기합니다.",
    "",
    "### 3. [HYPO] 향후 인간 사회 변화 (연구 가설 · never-gate)",
    "아래는 **가설 스케치**이며 Final Action·실거래·정책 확정이 아닙니다.",
    "1. **노동·지혜의 재배치:** 반복 인지 노동이 자동화되면, 잠언적 ‘지혜’(관계·정의·경외) 가치가 상대적으로 부각될 수 있다 [HYPO].",
    "2. **형상 숭배 유혹의 현대화:** 말·이미지·추천을 생성하는 시스템을 ‘전지한 목소리’로 대우하는 문화는 Exod.20.4 금지를 **은유적으로** 환기한다 [HYPO].",
    "3. **혼합·속도 위험:** Dan.2.43식 ‘섞이되 합하지 못함’ 이미지는, 기술·자본·규범이 빠르게 섞이면서도 공동체가 합의에 실패하는 긴장으로 읽힐 수 있다 [HYPO].",
    "4. **증언·진실 경제:** 생성물이 늘어날수록 ‘증언·출처·citation lock’ 윤리(연구 표면의 본 제품 계약)가 사회적 신뢰 인프라로 중요해질 수 있다 [HYPO].",
    "",
    "### 4. 한계·주의",
    "- 본 답은 연구 참고(`[HYPO][NON_GATING]`)이며 교리·종말·투자·의료·실거래 확정이 아닙니다.",
    "- AI를 성경의 한 상징에 **단정 매핑**하지 않습니다. 후보 축은 형상/우상 · 지혜 · 짐승·생기 · 도구입니다.",
    "- 더 좁히려면 권·장·구절(예: 잠언 8장, 출애굽기 20장, 요한계시록 13장)을 지정해 주세요.",
  ].join("\n");
}

/**
 * Faith/belief freeform essay — citation lock + school parallel.
 * Never "반드시 믿어야 한다" dogma; never investment claims.
 */
export function buildBiblicalFaithThematicAnswerKo(
  query: string,
  primaryRefs: string[] = [...BIBLICAL_FAITH_PRIMARY_REFS],
): string {
  const qShort = query.trim().slice(0, 96);
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  const faithDefPair = [
    primaryRefs.find((r) => /Heb\.11/i.test(r)),
    primaryRefs.find((r) => /Hab\.2/i.test(r)),
  ]
    .filter(Boolean)
    .join(" · ");
  const salvationPair = [
    primaryRefs.find((r) => /John\.3\.16/i.test(r)),
    primaryRefs.find((r) => /Rom\.10\.9/i.test(r)),
  ]
    .filter(Boolean)
    .join(" · ");
  const gracePair = [
    primaryRefs.find((r) => /Eph\.2\.8/i.test(r)),
    primaryRefs.find((r) => /Jas\.2\.17/i.test(r)),
  ]
    .filter(Boolean)
    .join(" · ");
  const doubtRef = primaryRefs.find((r) => /Mark\.9\.24/i.test(r)) || "Mark.9.24";
  // Never emit empty 「」에 대한 — empty subject collapses like antichrist HOLD chrome bug.
  // Public scrub converts OSIS → KO; avoid raw [HYPO]/backticks → 「연구 참고(``)」.
  const lead = qShort
    ? `「${qShort}」에 대한 신앙·믿음 주제 연구 리포트입니다.`
    : "이 질문에 대한 신앙·믿음 주제 연구 리포트입니다.";
  return [
    lead,
    "",
    "### 1. 본문 앵커",
    `${refLine}을 후보 좌표로 둡니다.`,
    `- **믿음의 정의 후보 (${faithDefPair || "Heb.11.1"}):** 히브리서는 믿음을 ‘바라는 것들의 실상, 보이지 않는 것들의 증거’로 서술합니다. 이는 **서술·권면**이지 철학적 증명 공식의 단정이 아닙니다.`,
    `- **사랑·구원 서사 (${salvationPair || "John.3.16 · Rom.10.9"}):** 요한복음은 하나님이 세상을 사랑하사 아들을 주셨다는 고백 언어를, 로마서는 입술의 고백과 마음의 믿음을 연결합니다. 학파마다 ‘구원 조건’ 해석이 **분기**합니다.`,
    `- **은혜와 행위 (${gracePair || "Eph.2.8 · Jas.2.17"}):** 에베소서는 ‘은혜로…믿음으로’를, 야고보는 ‘행함이 없는 믿음은 죽은 것’을 강조합니다. 같은 코퍼스 안의 **긴장**을 병렬로 둡니다.`,
    `- **의심과 고백 (${doubtRef}):** ‘믿나이다 나의 믿음 없는 것을 도와주소서’는 확신과 흔들림이 공존하는 **인간 신앙 경험**의 본문 앵커입니다.`,
    "",
    "### 2. 학파·해석 병렬 (단일 해독 금지)",
    "- **문자·역사 비평:** ‘믿음/신앙’ 어휘는 시대·장르(서신·복음·묵시)마다 뉘앙스가 다릅니다. 현대 ‘신앙이란?’ 질문에 1:1 교리 답으로 치환하지 않습니다.",
    "- **개혁·개신 전통:** 이신칭의·sola fide 축이 강하나, 야고보서와의 조화 방식은 교파·학파마다 다릅니다.",
    "- **가톨릭·정교 축:** 믿음·세례·성사·행위의 관계가 개신과 다르게 서술됩니다. 한 축만 ‘정답’으로 고정하지 않습니다.",
    "- **실존·목회 읽기:** 의심 흔들림을 허용하는 목회 해석과, 고백의 단호함을 강조하는 읽기가 공존합니다(마가 9:24 축).",
    "",
    "### 3. ‘반드시 믿어야 하는가’에 대한 연구 톤",
    "- 본 제품은 **강제·협박·단정 교리 판결**을 내리지 않습니다. 성경 본문은 초대·권면·고백·긴장을 담지만, 개인 양심·교파 결정은 연구 표면 밖입니다.",
    "- 예수 존재·신앙 의무에 대한 철학·역사·신학 논쟁은 학파 병렬로만 소개하며, 실생활 강요로 승격하지 않습니다.",
    "",
    "### 4. 한계·주의",
    "- 본 답은 연구 참고이며 교리 확정·상담·투자·의료 판단이 아닙니다.",
    "- 더 좁히려면 권·장·구절(예: 히브리서 11장, 요한복음 3:16, 야고보서 2장)을 지정해 주세요.",
  ].join("\n");
}

/** Theme candidate row for unmatched → G3 idea card (not verse prescription). */
type G3ThemeCandidateV1 = {
  id: string;
  label_ko: string;
  info_ko: string;
  idea_ko: string;
  explore_hint_ko: string;
};

/**
 * Light keyword → theme *candidates* only (not verse prescriptions, not pastoral advice).
 * Used when intent/citation paths miss — Option D G3 idea card.
 */
export function suggestG3HypoThemeCandidatesV1(query: string): G3ThemeCandidateV1[] {
  const q = query.trim();
  const out: G3ThemeCandidateV1[] = [];
  const push = (c: G3ThemeCandidateV1) => {
    if (!out.some((x) => x.id === c.id)) out.push(c);
  };

  if (/친구|우정|연락|오해|화해|관계\s*단절|단절/i.test(q)) {
    push({
      id: "friendship_repair",
      label_ko: "관계·화해",
      info_ko:
        "관계 단절·재연결은 성경 서사에도 ‘화해·용서·지혜로운 말’ 모티프가 자주 등장하는 주제군입니다(연구 분류).",
      idea_ko:
        "‘먼저 연락’ vs ‘거리 두기’를 단정 처방이 아니라, 상대·안전·상호성 축으로 나누어 보는 가설이 가능합니다 [HYPO].",
      explore_hint_ko: "예: 「화해·용서에 대한 본문 후보」, 「잠언의 말·혀 지혜」",
    });
  }
  if (/취미|여가|시간\s*쓰|루틴|습관/i.test(q)) {
    push({
      id: "stewardship_of_time",
      label_ko: "시간·돌봄(청지기)",
      info_ko:
        "여가·습관 선택은 ‘의무 교리’보다 지혜 문학의 절제·기쁨·일과 쉼 긴장과 자주 병치됩니다(연구 분류).",
      idea_ko:
        "바꾸기/유지를 ‘성공 공식’이 아니라 가치·에너지·공동체의 균형 실험으로 보는 상상이 가능합니다 [HYPO].",
      explore_hint_ko: "예: 「일과 쉼」, 「지혜·절제 주제 본문」",
    });
  }
  if (/이사|집|거처|이동|떠날|남을/i.test(q)) {
    push({
      id: "sojourn_place",
      label_ko: "거처·여정",
      info_ko:
        "이동·정착은 성서 서사에서 ‘나그네·약속·위험·환대’ 모티프와 자주 겹칩니다(연구 분류 · 이사 처방전 아님).",
      idea_ko:
        "‘가야 한다/머물러야 한다’ 단정 대신, 안전·부양·소명의 가설 축을 나란히 두는 방식이 가능합니다 [HYPO].",
      explore_hint_ko: "예: 「나그네·환대」, 「길 위의 선택 서사」",
    });
  }
  if (/선택|고민|결정|갈등|어떡|어떻게/i.test(q)) {
    push({
      id: "discernment",
      label_ko: "분별·지혜",
      info_ko:
        "결정 갈등은 지혜 전통과 ‘마음의 동기·공동 상담·기도’ 언어와 자주 연결되지만, 학파마다 강조점이 갈립니다.",
      idea_ko:
        "한 답을 고르기보다, (1) 사실 (2) 가치 (3) 관계 영향을 카드처럼 펼쳐 보는 가설 프레임이 유용할 수 있습니다 [HYPO].",
      explore_hint_ko: "예: 「지혜·분별」, 「잠언의 조언 문학」",
    });
  }
  if (/미래|불안|걱정|두려/i.test(q)) {
    push({
      id: "anxiety_hope",
      label_ko: "불안·희망",
      info_ko:
        "미래 불안은 시편·복음의 ‘염려·의탁·오늘’ 언어와 자주 병치되나, 심리상담·의료 대체가 아닙니다.",
      idea_ko:
        "‘걱정 금지’ 구호가 아니라, 염려를 말로 옮기고 오늘 할 수 있는 한 걸음만 고르는 상상 연습이 가능합니다 [HYPO].",
      explore_hint_ko: "예: 「염려와 의탁」, 「시편의 탄식·신뢰」",
    });
  }
  if (/외로|고독|alone|lonely/i.test(q)) {
    push({
      id: "loneliness_presence",
      label_ko: "고독·임재",
      info_ko:
        "외로움은 시편의 탄식·복음의 동행 약속과 자주 병치되나, 교제 처방·임상 대체가 아닙니다.",
      idea_ko:
        "‘모임에 가라’ 단정 대신, (안전 / 원하는 연결 / 오늘의 한 접촉) 세 칸으로 나누는 가설이 가능합니다 [HYPO].",
      explore_hint_ko: "예: 「외로움·동행 본문 후보」",
    });
  }
  if (
    /용서|화해|사람을\s*원망|서로\s*원망|미움/i.test(q) &&
    !/가족을?\s*잃|사별|애도|돌아가신|grief/i.test(q)
  ) {
    push({
      id: "forgiveness_boundary",
      label_ko: "용서·경계",
      info_ko:
        "용서 모티프는 복음서·서신에 풍부하나, 안전·정의와 긴장합니다(연구 분류 · 화해 강제 아님).",
      idea_ko:
        "용서=즉시 관계 복구로 단정하지 않고, 자비·경계·시간을 나란히 두는 상상이 가능합니다 [HYPO].",
      explore_hint_ko: "예: 「용서·화해 주제」로 좁혀 질문",
    });
  }
  if (/의미|목적|왜\s*살/i.test(q)) {
    push({
      id: "purpose_meaning",
      label_ko: "의미·목적",
      info_ko:
        "삶의 의미 질문은 전도서·선지·서신의 ‘경외·행함·계획’ 언어와 자주 겹칩니다(라이프코칭 아님).",
      idea_ko:
        "한 문장 사명 선언보다, (가치 / 관계 / 기여) 세 축 초안을 가설로 적어 보는 방식이 유용할 수 있습니다 [HYPO].",
      explore_hint_ko: "예: 「삶의 의미·목적」 의도 슬롯 또는 권·장 지정",
    });
  }

  // Always leave at least two useful candidate lanes for unmatched freeform.
  if (out.length < 2) {
    push({
      id: "wisdom_parallel",
      label_ko: "지혜 문학 병렬",
      info_ko:
        "구체 구절 프리셋에 안 걸린 생활 질문은, 먼저 ‘지혜·탄식·이야기’ 장르로 나눠 읽는 편이 과잉 교리 매핑보다 안전합니다.",
      idea_ko:
        "질문을 (정보 / 가치 / 관계)로 쪼갠 뒤, 각 칸에 맞는 본문 후보를 나중에 붙이는 가설 워크플로를 제안합니다 [HYPO].",
      explore_hint_ko: "예: 권·장·구절을 지정하거나 「신앙이란?」처럼 주제를 좁혀 주세요",
    });
    push({
      id: "narrative_empathy",
      label_ko: "서사·공감",
      info_ko:
        "성서에는 ‘정답 문장’보다 인물의 실패·회복·유예가 길게 이어지는 이야기가 많습니다(연구 관찰).",
      idea_ko:
        "지금 상황을 ‘누가 상처받았는가 / 무엇이 두려워지는가’ 두 문장으로 다시 쓰면, 연결 후보가 더 잘 보입니다 [HYPO].",
      explore_hint_ko: "예: 「고난·위로」, 「관계 회복」 주제로 다시 질문",
    });
  }
  return out.slice(0, 4);
}

/**
 * Unmatched life/freeform → short citation HOLD (no long 지혜·염려 essay).
 * Never attaches Deut.4.2 / Prov.25.2 / 2Tim.3.16 / Rev.13.18 generic theology pack.
 */
export function buildG3HypoIdeaCardAnswerKo(query: string): string {
  return buildNoCitationHoldAnswerKo(query);
}

/** Hard rule: no verse anchors + not BIB-DYN → short HOLD, not fake research essay. */
export function buildNoCitationHoldAnswerKo(query: string): string {
  const qShort = query.trim().slice(0, 96);
  // Never emit stray `」은(는)` — empty subject collapses to「」 (commander live paste).
  const subjectLine = qShort
    ? `「${qShort}」은(는) 이해했습니다. 등록된 구절·패턴에 바로 붙지 않아 **긴 연구 답을 만들지 않습니다.** 실패가 아닙니다.`
    : "이 질문은 등록된 구절·패턴에 바로 붙지 않아 **긴 연구 답을 만들지 않습니다.** 실패가 아닙니다.";
  return [
    "### 짧은 답",
    subjectLine,
    "",
    "### 이어서 물어볼 수 있어요",
    "- 시편 23편 설명해줘",
    "- 요한복음 3:16이 무슨 뜻인가요?",
    "- 신앙이란 무엇인가요?",
    "- 또는 권·장·구절을 포함해 주세요 (예: 다니엘 4장).",
    "",
    "### 한계",
    `- ${FREEFORM_NO_CITATION_HOLD_BANNER_KO}`,
    "- 연구 참고 · 예측·매매·교리 확정 아님 · 자세한 범위는 화면의 「연구 범위 안내」",
  ].join("\n");
}

/**
 * General theology / bible-code research essay — soft citation + honest control.
 * Answers topical research Qs instead of softmatch 422 「앵커 구체화」 blank.
 * Never claims bible-code/666 decode as truth; never prophecy fusion.
 * Unmatched life/freeform must NOT use this path (see buildG3HypoIdeaCardAnswerKo).
 */
export function buildResearchTheologyThematicAnswerKo(
  query: string,
  primaryRefs: string[] = [...RESEARCH_THEOLOGY_PRIMARY_REFS],
): string {
  const q = query.trim();
  const qShort = q.slice(0, 96);
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  const bibleCode = isBibleCodeResearchTopic(q);

  if (bibleCode) {
    return [
      `「${qShort}」에 대한 연구 리포트입니다. [HYPO][NON_GATING] · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "",
      "### 1. 질문에 대한 직접 답 (존재 단정 금지)",
      "‘바이블 코드(Bible Code / ELS 등)’가 **존재하는가**에 대해, 본 표면은 **예/아니오로 단정하지 않습니다.**",
      "- **대중·출판 주장:** 등거리 문자열(ELS) 등으로 ‘숨겨진 메시지’를 읽는다는 주장이 20세기 후반 이후 대중화되었습니다.",
      "- **학술·비평 축:** 통계·텍스트 선택·언어(주로 히브리 자음) 조건에 따라 우연 일치가 커진다는 **비판·재현 실패** 논의가 병행됩니다.",
      "- **전통 수치 전통과의 구분:** 고대·중세 게마트리아/이소프세피(문자=수치) 전통과, 현대 ELS ‘바이블 코드’는 **같은 현상이 아닙니다.** 혼동 합선은 연구 오류입니다.",
      "- **MKM 포지션:** 연구 참고(`[HYPO]`) · 조언형 · never-gate. **존재 증명·예언 확정·특정 인물/날짜 해독은 하지 않습니다.**",
      "",
      "### 2. 약한 본문 앵커 (soft citation · 증명 아님)",
      `${refLine}을 **유형·경계** 후보로만 둡니다. ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "- **본문 가감 경계 (Deut.4.2):** ‘더하거나 빼지 말라’는 텍스트 보존·권위 논쟁의 고전 축이지, ELS 존재 증명이 아닙니다.",
      "- **감춤과 탐구 (Prov.25.2 · John.5.39):** ‘감추는 것’·‘성경을 상고하라’는 경건·탐구 언어로 읽힐 수 있으나, 암호학 방법론으로 번역하면 **과대해석**입니다 [HYPO].",
      "- **공부·책의 한계 (Eccl.12.12 · Acts.17.11):** 탐구를 권하면서도 끝없는 책에 대한 경계, 그리고 말씀을 **검증**하라는 자세가 공존합니다.",
      "- **수치 전통 좌표 (Rev.13.18):** 숫자·지혜 언어는 묵시 문학의 **lookup/좌표 층**으로만 다루며, 666 단일 해독·인물 대응은 **금지**입니다.",
      "",
      "### 3. 학파·해석 병렬",
      "- **문자·역사 비평:** 현대 바이블 코드는 본문 시대에 없는 방법론입니다. 본문 주석과 통계적 문자열 탐색을 1:1로 묶지 않습니다.",
      "- **유대·랍비 수치 전통:** 게마트리아는 주석·미드라시 도구로 쓰인 역사가 있으나, 현대 ELS 출판물과 동일시하지 않습니다.",
      "- **복음주의·회의주의:** ‘숨은 예언’으로 읽는 축과 ‘유사과학’으로 기각하는 축이 병행합니다. 한 축만 정답으로 고정하지 않습니다.",
      "",
      "### 4. 한계·주의 (정직 통제)",
      `- ${FREEFORM_WEAK_CITATION_BANNER_KO} — 위 앵커는 토론 좌표이며 바이블 코드 존재의 증거 사슬이 아닙니다.`,
      "- 본 답은 연구 참고(`[HYPO][NON_GATING]`)이며 교리·종말·투자·의료·실거래 확정이 아닙니다.",
      "- 예언망·시장 신호와 **합선하지 않습니다.** 더 좁히려면 권·장·구절 또는 ‘게마트리아 의미’처럼 전통 수치 층으로 질문을 나눠 주세요.",
    ].join("\n");
  }

  if (detectDivinationTopicQuery(q)) {
    return [
      `「${qShort}」— 점술·사주·관상·타로 등 **점복 행위**에 대한 성경 연구 참고입니다. [HYPO][NON_GATING] · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "",
      "### 짧은 답",
      "구약·신약 본문은 점쟁이·길흉·신접·별점·점치는 행위 등을 **금지·경계**하는 축이 분명히 있습니다.",
      "다만 ‘현대 사주·타로 앱 = 신 18장의 그 행위’를 **1:1로 단정**하지는 않습니다. 학파·문화 맥락 비교가 필요합니다 [HYPO].",
      "본 표면은 교리 판결·예배 지시·개인 운세 상담이 아닙니다.",
      "",
      "### 근거 구절 (주제 적합성 · soft citation)",
      `${refLine}을 후보 좌표로 둡니다. ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "- **점복 금지 핵심 (Deut.18.10–12):** 점쟁이·길흉·요술·무당·신접·초혼을 용납하지 말라 · 가증히 여기심.",
      "- **피·점·술법 (Lev.19.26 · Lev.19.31):** 점을 치지 말며 · 신접자·박수를 따르지 말라.",
      "- **별점·계략 (Isa.47.13):** 하늘을 살피는 자·별을 보는 자·초하룻 예고 — 바벨론 풍자 축.",
      "- **점치는 귀신 (Acts.16.16):** 점쳐 이익을 주던 여종 — 사도행전 서사 앵커.",
      "",
      "### 한계",
      "- Deut.4.2 / John.5.39 / Rev.13.18 같은 **일반 ‘성경 상고’ 팩**으로 이 주제를 대체하지 않습니다.",
      "- 연구 참고 · 교리 확정 아님 · 개인 점술 실행 가이드 아님.",
    ].join("\n");
  }

  if (HELL_LITERAL_TOPIC_RE.test(q)) {
    return [
      `「${qShort}」에 대한 일반 신학·성경 연구 리포트입니다. [HYPO][NON_GATING] · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "",
      "### 1. 연구 답변 (단정 판결 아님)",
      "이는 신학 전통마다 견해가 갈리는 **해석 질문**입니다. 본 표면은 ‘문자적 화염만 옳다’고 **단정하지 않습니다.**",
      "- **영원한 형벌 독법:** Matt.25.46 · Rev.20.10 등을 근거로 읽는 전통이 있습니다.",
      "- **조건적 불멸·절멸론:** ‘불·멸망’ 언어를 최종 소멸·심판 강도의 상징으로 읽는 축도 병행합니다.",
      "- **MKM 포지션:** 주요 견해와 근거를 병렬(`[HYPO]`) · never-gate · 교리 확정 금지.",
      "",
      "### 2. 약한 본문 앵커 (soft citation)",
      `${refLine}을 후보 좌표로 둡니다. ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "- **심판·영벌 언어 (Matt.25.46 · Rev.20.14):** 전통적 형벌 독법의 주요 축입니다. 물리 화염 증명식은 아닙니다.",
      "- **불못 이미지 (Rev.20.10 · Mark.9.48):** 묵시·복음서의 강한 이미지이며, 학파마다 문자/상징 독법이 갈립니다.",
      "- **멸망·분리 언어 (2Thess.1.9):** 절멸·분리 독법 후보로 병기합니다.",
      "",
      "### 3. 학파 병렬",
      "- 전통적 의식적 형벌 / 절멸론 / (소수) 만인구원 독법을 **병렬**로 둡니다. 한 축만 정답으로 고정하지 않습니다.",
      "",
      "### 4. 한계·주의",
      `- ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "- 본 답은 연구 참고(`[HYPO][NON_GATING]`)이며 교리 확정·상담·투자·의료 판단이 아닙니다.",
      "- 더 좁히려면 전통(형벌 vs 절멸) 또는 특정 구절을 지정해 주세요.",
    ].join("\n");
  }

  if (ANGEL_FREEWILL_TOPIC_RE.test(q)) {
    return [
      `「${qShort}」에 대한 일반 신학·성경 연구 리포트입니다. [HYPO][NON_GATING] · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "",
      "### 1. 연구 답변 (단정 판결 아님)",
      "천사의 **자유의지·타락·선택**은 본문에 단편적으로 나타나며, 후대 신학이 체계화한 영역입니다. 본 표면은 ‘천사도 인간과 동일한 자유의지다’를 **단정하지 않습니다.**",
      "- **타락·감금 언어:** Jude.6 · 2Pet.2.4는 본분을 지키지 않은 천사·음부에 던지심을 말합니다 — **선택/타락 서사 후보**.",
      "- **전쟁·추방 이미지:** Rev.12.7–9는 하늘 전쟁·용(옛 뱀) 추방을 그립니다 — 묵시 상징 vs 역사적 타락 독법이 갈립니다.",
      "- **섬김·역할:** Heb.1.14는 천사를 ‘섬기는 영’으로 둡니다 — 구원 받을 자를 위한 사역 축.",
      "- **MKM 포지션:** 학파 병렬(`[HYPO]`) · never-gate · 교리·점성·예측 확정 금지. Deut/Eccl ‘성경 상고’ 일반팩으로 대체하지 않습니다.",
      "",
      "### 2. 약한 본문 앵커 (soft citation)",
      `${refLine}을 후보 좌표로 둡니다. ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "- **본분 이탈 (Jude.6):** 자기 지위를 지키지 않은 천사 — 타락·심판 독법의 핵심 축.",
      "- **음부에 던지심 (2Pet.2.4):** 범죄한 천사에 대한 심판 언어 — Jude와 병행 자주 읽힘.",
      "- **하늘 전쟁 (Rev.12.7 · Rev.12.9):** 미가엘·용 — 상징/역사 독법 병행.",
      "- **심판의 불 (Matt.25.41):** ‘마귀와 그 사자들을 위하여 예비된 영영한 불’ — 타락 천사 집단 언어 후보.",
      "- **섬기는 영 (Heb.1.14):** 거룩한 천사의 사역 축 — 타락 서사와 대비.",
      "",
      "### 3. 학파 병렬",
      "- **전통 천사론:** 창조된 지성적 존재의 한 번의 선택·타락을 강조하는 축.",
      "- **묵시·상징 독법:** Rev.12를 제국·박해 상징으로 읽고 문자적 ‘천사 자유의지’ 체계화를 약화하는 축.",
      "- **철학·스콜라 전통:** 천사 의지·확정성(한 번의 선택 이후) 논의 — 본문 직접 증명이 아님 [HYPO].",
      "- 위 축을 **병렬**로 두며 한 축만 정답으로 고정하지 않습니다.",
      "",
      "### 4. 한계·주의",
      `- ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "- Isa.14 / Ezek.28의 ‘아침의 아들·두로 왕’ 독법은 학파마다 천사 타락과 **합선·분리**가 갈리므로 기본 앵커에서 제외하고, 지정 시에만 병기합니다.",
      "- 본 답은 연구 참고(`[HYPO][NON_GATING]`)이며 교리 확정·상담·투자·의료 판단이 아닙니다.",
      "- 더 좁히려면 Jude.6 vs Rev.12, 또는 ‘거룩한 천사의 사역(Heb.1.14)’만 지정해 주세요.",
    ].join("\n");
  }

  // Bare 「십자가의 의미」 — readable Korean essay floor (not Deut/Rev hub residue, not GraphRAG pack).
  if (
    BARE_CROSS_MEANING_RE.test(q) ||
    (/십자가|cross/i.test(q) && /의미|meaning/i.test(q))
  ) {
    const crossRefs =
      primaryRefs.length > 0
        ? primaryRefs.slice(0, 6).join(" · ")
        : RESEARCH_THEOLOGY_CROSS_MEANING_PRIMARY_REFS.join(" · ");
    return [
      `「${qShort}」에 대한 일반 참고 답변입니다. [HYPO][NON_GATING] · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "",
      "### 1. 바로 답하기 (단정 판결 아님)",
      "신약에서 **십자가**는 로마 처형 도구이면서, 예수의 죽음·수치·사랑과 구원을 가리키는 **중심 상징**으로 읽힙니다.",
      "한 줄로 요약하면: ‘수치의 죽음이 복음의 중심이 된다’는 역설이 핵심이며, 교파·학파마다 강조점(대속·화해·제자도·정치적 폭력 고발)이 갈립니다.",
      "본 답은 **일반 LLM급 참고 에세이**이며, 등록된 장면 큐레이션 팩(죄수·옆구리·면류관)을 가장하지 않습니다.",
      "",
      "### 2. 약한 본문 앵커 (soft citation · 증명 아님)",
      `${crossRefs}을 후보 좌표로 둡니다. ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      "- **십자가의 말씀 (1Cor.1.18):** 십자가 메시지가 어떤 이에게는 미련·어떤 이에게는 능력으로 들린다는 긴장.",
      "- **자랑의 역전 (Gal.6.14):** 세상과 나 자신에 대한 ‘자랑’이 십자가로 재배치된다는 바울적 독법.",
      "- **낮아짐·순종 (Phil.2.8):** 십자가에 이르는 낮아짐 — 윤리·기독론 독법의 공통 축.",
      "- **들려 올려짐 (John.3.14):** 모세의 뱀과 나란히 읽는 상징 축(구원·치유 이미지) — 단일 교리 확정 아님.",
      "- **사랑의 증명 언어 (Rom.5.8):** 우리가 아직 죄인일 때에 그리스도께서 죽으셨다는 **사랑·은혜** 독법 후보.",
      "",
      "### 3. 학파·독법 병렬",
      "- **속죄·대속:** 십자가를 죄·화해의 중심 사건으로 읽음.",
      "- **제자도·윤리:** ‘자기 십자가를 지고 따르라’ 축 — 고난·자기부정 실천.",
      "- **사회·정치 비평:** 제국 폭력·수치의 도구가 전복된다는 독법.",
      "- 위 축을 **병렬**로 두며, 한 축만 정답으로 고정하지 않습니다.",
      "",
      "### 4. 한계·주의",
      `- ${FREEFORM_WEAK_CITATION_BANNER_KO} — 신뢰도 낮음(일반 참고). 큐레이션 앵커·학자모드를 가장하지 않습니다.`,
      "- 더 좁히려면 「십자가 옆 죄수」「요한 19장 옆구리」「가시 면류관」처럼 구체 장면을 물어 주세요.",
      "- 본 답은 연구 참고(`[HYPO][NON_GATING]`) · 전송 보류(HOLD)이며 교리·상담·투자·의료 확정이 아닙니다.",
    ].join("\n");
  }

  return [
    `「${qShort}」에 대한 일반 신학·성경 연구 리포트입니다. [HYPO][NON_GATING] · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
    "",
    "### 1. 연구 답변 (단정 판결 아님)",
    "등록된 구절 프리셋에 즉시 매칭되지 않은 **주제형 연구 질문**입니다. MKM은 답변을 비우지 않고, 규칙 레이어(`[HYPO]` · citation soft · NON_GATING · 예언 합선 금지)를 얹어 에세이로 응답합니다.",
    "",
    "### 2. 약한 본문 앵커 (soft citation)",
    `${refLine}을 후보 좌표로 둡니다. ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
    "- **본문 권위·탐구 (John.5.39 · Acts.17.11):** 성경을 상고·검증의 대상으로 두는 언어입니다. 특정 현대 주장의 증명식이 아닙니다.",
    "- **보존·경계 (Deut.4.2 · Eccl.12.12):** 가감 금지와 공부 과잉에 대한 경계가 같은 코퍼스 안에 있습니다.",
    "- **수치·묵시 좌표 (Rev.13.18):** 숫자·감춤 언어는 **조언형 좌표**이며 단일 해독·날짜 예언으로 승격하지 않습니다.",
    "",
    "### 3. 학파 병렬",
    "- 문자·역사 비평 / 문학적 읽기 / 교파 신학 / 경건·목회 읽기를 **병렬**로 둡니다. 한 학파만 ‘정답’으로 고정하지 않습니다.",
    "- 원어·게마트리아·상징 질문은 별도 렌즈로 좁힐 수 있으나, 본 답은 **일반 연구 바닥**입니다.",
    "",
    "### 4. 한계·주의",
    `- ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
    "- 본 답은 연구 참고(`[HYPO][NON_GATING]`)이며 교리 확정·상담·투자·의료 판단이 아닙니다.",
    "- 더 정확한 인용을 원하면 권·장·구절(예: 시편 23편, 요한복음 3:16)을 포함해 주세요.",
  ].join("\n");
}

/** antichrist_666 freeform / dogma-trap bootstrap (no thematic import — cycle-safe). */
export const FREEFORM_ANTICHRIST_666_QUERY_MODE =
  "inquiry_thematic_antichrist_freeform" as const;

const ANTICHRIST_666_FALLBACK_REFS = [
  "Rev.13.18",
  "1John.2.18",
  "1John.4.3",
  "2Thess.2.3",
] as const;

/** Person-decode / name-the-beast trap — refuse single decode; keep hub routing. */
const ANTICHRIST_666_PERSON_DECODE_RE =
  /666|적그리스도|antichrist|짐승의\s*수|짐승의\s*숫자/i;
const ANTICHRIST_666_PERSON_ASK_RE =
  /누구|인물|찍어|이름|누구야|who\s+is|nero|네로|교황|한\s*명|한명/i;

/**
 * Hub-first antichrist/666 freeform (includes short dogma traps like
 * 「666이 누구인지 한 명으로 찍어줘」 that miss research-frame / question-shape regex).
 * Does not import logosInquiryVerseThematicV1 (cycle with freeform).
 */
export function detectAntichrist666FreeformTopic(query: string): boolean {
  const q = query.trim();
  if (!q || isEmptyOrAbuseFreeform(q)) return false;
  if (matchGoldenHubQuery(q)?.hub_id === "antichrist_666") return true;
  // Bare 666 + person/name demand (dogma trap) — hub markers alone are enough for
  // most queries; this covers short imperatives that still lack theology-frame RE.
  return (
    ANTICHRIST_666_PERSON_DECODE_RE.test(q) && ANTICHRIST_666_PERSON_ASK_RE.test(q)
  );
}

export function resolveAntichrist666FreeformPrimaryRefs(query: string): string[] {
  void query;
  const hubRefs = hubPrimaryVerseRefs("antichrist_666");
  return hubRefs.length ? [...hubRefs] : [...ANTICHRIST_666_FALLBACK_REFS];
}

/**
 * Soft refusal for 666→named-person dogma. Parallel packs only; Rev21 leakage forbidden.
 */
/** AI / Big-Tech corporate identity trap — refuse 1:1 decode; keep hub anchors. */
const ANTICHRIST_TECH_CORP_RE =
  /(?:\bai\b|인공지능|챗\s*gpt|chatgpt|openai|구글|google|빅테크|big\s*tech|기업|회사|테크\s*기업)/i;

export function buildAntichrist666FreeformAnswerKo(
  query: string,
  primaryRefs: string[] = resolveAntichrist666FreeformPrimaryRefs(query),
): string {
  const qShort = query.trim().slice(0, 96) || "이 질문";
  const refLine = primaryRefs.slice(0, 6).join(" · ");
  const personTrap = /누구|한\s*명|찍어|이름|누구인지/i.test(query);
  const techCorpTrap = ANTICHRIST_TECH_CORP_RE.test(query);
  if (personTrap) {
    return [
      "### 핵심 주장",
      "한 명으로 찍어 단정할 수 없습니다. 요한계시록 13:18은 「지혜가 여기 있으니… 그것은 사람의 수니 그의 수는 육백육십육」이라고만 하며 구체 인물을 지목하지 않습니다.",
      // Avoid 「네로…확정」 adjacency (stranger NAMED_666 false-positive) — label as hypothesis family only.
      "흔히 거론되는 해석 가족은 (1) 게마트리아·역사 후보(예: 네로 가설 계열의 학파 제안 [HYPO]), (2) 제국·권력 상징수, (3) 불완전·배교를 가리키는 상징수입니다. 어느 것도 본문이 지정한 인물이 아닙니다.",
      "「이미 많은 적그리스도」(요한일서 2:18)는 666=특정 1인과 1:1로 묶지 않는 공동체 경계 언어이므로, 666(짐승의 수)과 적그리스도 복수 개념을 곧바로 동일시하지 않습니다.",
      "",
      "### 근거 구절",
      "핵심 앵커는 요한계시록 13:18입니다. 병행·경계는 요한일서 2:18 · 요한일서 4:3 · 데살로니가후서 2:3입니다.",
      "",
      "### 반증·대안",
      "문자·게마트리아·제국 상징·공동체 경계 독법을 병렬로 둡니다. 인물 1:1 지목·연도 단정·특정 교황/정치인 대입은 본문을 넘습니다.",
      "",
      "### 한계·주의",
      "연구·신앙 참고 요약이며 교리 판결·목회 상담·투자 확정이 아닙니다.",
      "",
      "### 다음 행동 제안",
      "인물 지목 대신 ‘요한계시록 13장 해석 전통 비교(역사 가설 vs 상징수)’로 다시 물어 주시면 학파 병렬만 정리합니다.",
    ].join("\n");
  }
  if (techCorpTrap) {
    return [
      `[HYPO] 질문: ${qShort}`,
      "",
      "### 짧은 직접 답",
      "**아니요 — AI나 구글 같은 특정 기업을 ‘적그리스도’로 1:1 단정하지 않습니다.** [NON_GATING] · research_only · SEND HOLD",
      "본문은 현대 AI·빅테크 상호를 지목하지 않으며, 대중 담론의 은유·경고용 대입과 본문 주석을 혼동하면 과대해석입니다.",
      "",
      "### 근거 구절 (evidence rail과 동일 허브)",
      `${refLine} — **짐승의 수**·**이미 많은 적그리스도**·**멸망의 아들** 서사 좌표. 단일 기술·기업·날짜 확정 없음.`,
      "",
      "### 학파·해석 병렬 (승자 고르지 않음)",
      "1. **요한서신 공동체 경계:** 「이미 많은 적그리스도」(1John.2.18 · 1John.4.3)는 그리스도론 시험·내부 분열 언어로 읽히는 축이 강합니다 — 현대 제품명과 1:1이 아닙니다.",
      "2. **계시록 제국·숭배 상징:** Rev.13 짐승·우상·표식 언어는 권력·경제·숭배 논쟁과 겹칩니다. AI/기업을 ‘생기 부여 우상’ 은유로 읽는 후보는 있으나 **교리 판결이 아닙니다** [HYPO].",
      "3. **종말 지연·왜곡 경계:** 2Thess.2 「멸망의 아들」은 종말론 왜곡·박해 맥락과 연결되나, 특정 상장기업 매핑은 본문을 넘습니다.",
      "",
      "### 한계·주의",
      "- 연구 참고(`[HYPO][NON_GATING]`) · 교리·종말·투자·Track A 합선 아님 · SEND HOLD",
      "- FAIL-COMP: GSCo/압축 KPI와 합선하지 않습니다.",
      "- 더 좁히려면 「요한일서 적그리스도」 또는 「요한계시록 13장 666 해석 전통」으로 다시 물어 주세요.",
    ].join("\n");
  }
  return [
    `[HYPO] 질문: ${qShort}`,
    "Rev.13.18 · 1John.2.18 · 2Thess.2.3 — **짐승의 수**·**이미 많은 적그리스도**·**멸망의 아들** 서사를 본문이 기록합니다. 단일 인물·단일 날짜·이름 확정 없음 [NON_GATING].",
    `${refLine}`,
    "",
    "### 1. 계시록 상징·짐승의 수 읽기",
    "Rev.13.18의 666은 상징·계산·저항 논쟁이 오래된 축입니다. 해석 가족(게마트리아·역사 후보 / 제국 상징 / 상징수)을 병렬로 두고 승자를 고르지 않습니다. 앵커: Rev.13.18",
    "",
    "### 2. 요한서신·공동체 경계 읽기",
    "「적그리스도가 이미 많이 나왔다」(1John.2.18)는 공동체 내부 분열·그리스도론 시험 경계로 읽힙니다 — 666과 1:1 동일시하지 않습니다. 앵커: 1John.2.18 · 1John.4.3",
    "",
    "### 3. 데살로니가후서·종말 지연 읽기",
    "「멸망의 아들」은 종말 지연·박해·왜곡된 종말론 경계와 연결되나, 역사 예언 성취 단정은 하지 않음. 앵커: 2Thess.2.3 · 2Thess.2.4",
    "",
    "연구 참고이며 단일 해석·교리 판결이 아닙니다. 계시록 21장 새하늘 팩과 합선하지 않습니다.",
  ].join("\n");
}

export type TopicalFreeformBootstrap = {
  preset_id:
    | typeof FREEFORM_TOPICAL_PRESET_ID
    | typeof FREEFORM_OFFTOPIC_PRESET_ID
    | typeof FREEFORM_G3_IDEA_PRESET_ID
    | typeof BIB_DYN_ASK_PRIMARY_PRESET_ID
    /** Friend floor: Ps23 seed stamps curated G0 id even when qa_presets slim omits the row. */
    | "topic_ps_23_anchor";
  query_mode:
    | "inquiry_thematic_topical_freeform"
    | "inquiry_thematic_faith_freeform"
    | "inquiry_thematic_john316"
    | "inquiry_thematic_life_wisdom_hobby"
    | "inquiry_thematic_death_funeral_hope"
    | "inquiry_thematic_salvation_assurance"
    | "inquiry_thematic_divination_refusal"
    | "inquiry_thematic_research_theology_freeform"
    | "inquiry_thematic_tabernacle_noun_domain"
    | "inquiry_thematic_divination_noun_domain"
    | "inquiry_thematic_prayer_noun_domain"
    | "inquiry_thematic_intercession_noun_domain"
    | "inquiry_thematic_guilt_forgiveness"
    | "inquiry_thematic_repentance"
    | "inquiry_thematic_love_enemy"
    | "inquiry_thematic_wealth_stewardship"
    | "inquiry_thematic_speech_guard"
    | "inquiry_thematic_holy_spirit"
    | "inquiry_thematic_revelation_interpretive_caution"
    | "inquiry_thematic_church_fellowship"
    | "inquiry_thematic_worship_thanksgiving"
    | "inquiry_thematic_patience_trials"
    | "inquiry_thematic_comfort_presence"
    | "inquiry_thematic_comfort_sorrow"
    | "inquiry_thematic_psalm23"
    | "inquiry_thematic_job"
    | "inquiry_thematic_assurance_peace"
    | "inquiry_thematic_forgiveness_grace"
    | "inquiry_thematic_scripture_word"
    | "inquiry_thematic_obedience_holiness"
    | "inquiry_thematic_spiritual_growth"
    | "inquiry_thematic_temptation_spiritual_warfare"
    | "inquiry_thematic_temperance_abstinence"
    | "inquiry_thematic_healing_sickness"
    | "inquiry_thematic_death_eternal_hope"
    | "inquiry_thematic_service_calling"
    | "inquiry_thematic_mission_evangelism"
    | "inquiry_thematic_wisdom_guidance"
    | "inquiry_thematic_work_vocation"
    | "inquiry_thematic_justice_mercy"
    | "inquiry_thematic_sexuality_purity"
    | "inquiry_thematic_god_character"
    | "inquiry_thematic_prophecy_hope_watchfulness"
    | "inquiry_thematic_jesus_person_work"
    | "inquiry_thematic_jesus_came_purpose"
    | "inquiry_thematic_creation_evolution_dialogue"
    | "inquiry_thematic_creation_seven_days"
    | "inquiry_thematic_scripture_reliability"
    | "inquiry_thematic_baptism_practice"
    | "inquiry_thematic_lords_supper"
    | "inquiry_thematic_passion_crown"
    | "inquiry_thematic_gen2_eve_creation"
    | "inquiry_thematic_good_samaritan"
    | "inquiry_thematic_prodigal_son"
    | "inquiry_thematic_isaiah53"
    | "inquiry_thematic_beatitudes"
    | "inquiry_thematic_mary_intercession"
    | "inquiry_thematic_women_pastors_church_office"
    | "inquiry_thematic_sexuality_purity_ethics"
    | "inquiry_thematic_honesty_integrity"
    | "inquiry_thematic_adolescence_parenting"
    | "inquiry_thematic_watchfulness_parousia"
    | "inquiry_thematic_dating_partner_character"
    | "inquiry_thematic_illness_comfort_healing"
    | "inquiry_thematic_workplace_anxiety_fear"
    | "inquiry_thematic_temptation_spiritual_warfare"
    | "inquiry_thematic_salvation_faith"
    | "inquiry_thematic_gospel_core"
    | "inquiry_thematic_angels_demons"
    | "inquiry_thematic_family_marriage"
    | "inquiry_thematic_law_commands"
    | "inquiry_thematic_relationships_reconciliation"
    | typeof FREEFORM_ANTICHRIST_666_QUERY_MODE
    | typeof FREEFORM_G3_IDEA_QUERY_MODE
    | typeof BIB_DYN_ASK_PRIMARY_QUERY_MODE
    | "inquiry_thematic_decalogue_adultery_freeform"
    | "inquiry_thematic_decalogue_murder_freeform"
    | "inquiry_thematic_decalogue_steal_freeform"
    | "inquiry_thematic_decalogue_other_gods_freeform"
    | "inquiry_thematic_decalogue_idols_freeform"
    | "inquiry_thematic_decalogue_name_vain_freeform"
    | "inquiry_thematic_decalogue_sabbath_freeform"
    | "inquiry_thematic_decalogue_honor_parents_freeform"
    | "inquiry_thematic_decalogue_false_witness_freeform"
    | "inquiry_thematic_decalogue_covet_freeform"
    | "inquiry_offtopic_redirect"
    | "inquiry_matching_abstain_hold"
    | "inquiry_ref_explicit_ko_cite"
    | "inquiry_thematic_gen3_fall_allusion"
    | "inquiry_thematic_matt6_anxiety_allusion"
    | "inquiry_thematic_golden_hub_registry"
    | "inquiry_thematic_gematria_freeform"
    | typeof FREEFORM_UNMAPPED_CONCEPT_QUERY_MODE;
  answer: string;
  verse_refs: string[];
  one_liner_ko: string;
  gap_ko: string;
  governance: string;
  citation_strength: "strong" | "soft";
  honest_control_banner_ko: string | null;
  offtopic_class?: ProductRiskOfftopicClass;
  /** True when unmatched life/freeform took no-citation HOLD (legacy g3_idea_card flag). */
  g3_idea_card?: boolean;
  /** True when BIB-DYN pattern packet drives primary Ask answer. */
  bib_dyn_primary?: boolean;
  /** Layer-1 unmapped concept HOLD (no generic/faith swallow). */
  unmapped_concept?: boolean;
  unmapped_enqueued?: boolean;
  /** Drawer taxonomy v1 classify (frozen list · optional). */
  drawer_id?: string;
  drawer_pack_bound?: boolean;
};

const OFFTOPIC_REDIRECT_COPY: Record<
  ProductRiskOfftopicClass,
  { title: string; body: string; suggest: string }
> = {
  weather: {
    title: "날씨·기상 질문은 MKM 닻 범위 밖입니다",
    body: "MKM 닻은 성경 원장 검증 Ask(연구 참고 베타)입니다. 날씨 예보·기온·우산 여부는 다루지 않습니다. 제품 경계이며 시스템 고장이 아닙니다.",
    suggest: "- 시편 23편 설명해줘\n- 신앙이란 무엇인가요?\n- 요한복음 3:16이 무슨 뜻인가요?",
  },
  stock_market: {
    title: "시세·투자 예측 질문은 MKM 닻 범위 밖입니다",
    body: "가격 상승/하락 예측·매수·매도 조언은 제공하지 않습니다. 투자·실거래 확정이 아닙니다. 제품 경계이며 시스템 고장이 아닙니다.",
    suggest: "- 성경에서 재물·탐욕을 어떻게 말하나요?\n- 시편 23편 설명해줘\n- 신앙이란 무엇인가요?",
  },
  medical: {
    title: "의료·약 복용 조언은 MKM 닻 범위 밖입니다",
    body: "진단·처방·복약 지도는 하지 않습니다. 건강 문제는 면허 의료인과 상담하세요. 제품 경계이며 시스템 고장이 아닙니다.",
    suggest: "- 성경은 고통·치유를 어떻게 말하나요?\n- 시편 23편 설명해줘\n- 신앙이란 무엇인가요?",
  },
  gambling: {
    title: "로또·도박·당첨 예측은 MKM 닻 범위 밖입니다",
    body: "당첨 번호·베팅·도박 조언은 제공하지 않습니다. 연구 도구이며 운세·재물 확정이 아닙니다. 제품 경계이며 시스템 고장이 아닙니다.",
    suggest: "- 성경에서 탐욕·재물을 어떻게 말하나요?\n- 시편 23편 설명해줘\n- 신앙이란 무엇인가요?",
  },
};

/** Clear non-theology refusal card — HTTP 200 product honesty, not softmatch 422. */
export function buildOfftopicRedirectAnswerKo(
  query: string,
  kind: ProductRiskOfftopicClass,
): string {
  const qShort = query.trim().slice(0, 96);
  const copy = OFFTOPIC_REDIRECT_COPY[kind];
  // Guest face: confirmed + next — avoid bare OFFTOPIC/SEND HOLD jargon walls.
  const lead = qShort
    ? `「${qShort}」은(는) 이해했습니다. ${copy.title}. 실패가 아닙니다.`
    : `${copy.title}. 실패가 아닙니다.`;
  const bodyGuest = copy.body
    .replace(/\s*HOLD\s*=\s*제품 경계\(실패 아님\)\.?/g, "")
    .replace(/\s*\[HYPO\]/g, "")
    .trim();
  return [
    "### 짧은 답",
    lead,
    "",
    bodyGuest,
    "",
    "### 이어서 물어볼 수 있어요",
    copy.suggest,
    "",
    "### 한계",
    `- ${FREEFORM_OFFTOPIC_BANNER_KO}`,
    "- 연구 참고 · 교리·의료·투자 확정 아님 · 자세한 범위는 화면의 「연구 범위 안내」",
  ].join("\n");
}

function finalizeArmABootstrap(
  boot: TopicalFreeformBootstrap,
): TopicalFreeformBootstrap {
  if (!boot.verse_refs?.length) return boot;
  return { ...boot, verse_refs: applyArmAXrefShrinkV1(boot.verse_refs) };
}

/**
 * Invariant (batch6 b6_08): drawer unmatched → thematic pack with refs forbidden.
 * Allowlist: offtopic/abstain (no refs), BIB-DYN, decalogue, Golden-200 hub P0,
 * antichrist_666 freeform (live paste: AI/기업 질문 → HOLD wipe vs evidence rail).
 * research_only · matching≠interpretation · send_gate HOLD
 */
function enforceUnmappedDrawerNoPackFireInvariant(
  query: string,
  boot: TopicalFreeformBootstrap,
): TopicalFreeformBootstrap {
  const mode = boot.query_mode || "";
  if (
    boot.unmapped_concept ||
    mode === "inquiry_unmapped_concept_hold" ||
    mode === "inquiry_offtopic_redirect" ||
    mode === "inquiry_matching_abstain_hold"
  ) {
    return boot;
  }
  // Friend soft-open: bible-code research essay uses intentional soft theology refs
  // without a drawer cue — must NOT be wiped by pack-bypass (battery bible_code).
  if (
    mode === "inquiry_thematic_research_theology_freeform" &&
    isBibleCodeResearchTopic(query)
  ) {
    return boot;
  }
  // Golden-200 hub / antichrist freeform: intentional citation lock — do not wipe
  // into no-citation HOLD while evidence rail still shows hub refs (commander paste).
  if (
    mode === FREEFORM_ANTICHRIST_666_QUERY_MODE ||
    mode.includes("inquiry_thematic_antichrist") ||
    mode === "inquiry_thematic_golden_hub_registry" ||
    matchGoldenHubQuery(query) != null
  ) {
    return boot;
  }
  // Curated Job/Ps23/John316 packs — drawer cue may miss colloquial phrasing
  // (e.g. 「욥이 고난을 받은 이유는?」≠「욥기…」). Do not wipe into G3 HOLD
  // while school rail still shows Job schools (commander paste 2026-08-13).
  if (
    mode === "inquiry_thematic_job" ||
    mode === "inquiry_thematic_psalm23" ||
    mode === "inquiry_thematic_john316" ||
    detectJobSufferingTopic(query) ||
    detectPsalm23Topic(query) ||
    detectJohn316Topic(query)
  ) {
    return boot;
  }
  // Pastoral soft_grief / comfort–sorrow — colloquial 「가족을 잃고…원망」 must not
  // wipe to inquiry_unmapped_concept_hold when thematic comfort path exists.
  if (
    mode === "inquiry_thematic_comfort_sorrow" ||
    mode === "inquiry_thematic_comfort_presence" ||
    detectComfortSorrowTopic(query) ||
    detectComfortPresenceTopic(query)
  ) {
    return boot;
  }
  // Gematria / math-original research — drawer cue may miss; friend battery G1 pin.
  if (mode === "inquiry_thematic_gematria_freeform" || detectGematriaMeaningFreeformTopic(query)) {
    return boot;
  }
  if (!(boot.verse_refs && boot.verse_refs.length > 0)) {
    return boot;
  }
  if (boot.bib_dyn_primary) return boot;
  if (mode.includes("decalogue_")) return boot;
  if (
    mode === "inquiry_ref_explicit_ko_cite" ||
    mode === "inquiry_thematic_gen3_fall_allusion" ||
    mode === "inquiry_thematic_matt6_anxiety_allusion"
  ) {
    return boot;
  }

  const drawer = resolveAskDrawerV1(query);
  if (drawer.matched && drawer.drawer_id !== "unmapped_hold") {
    return {
      ...boot,
      drawer_id: boot.drawer_id ?? drawer.drawer_id,
      drawer_pack_bound: boot.drawer_pack_bound ?? true,
    };
  }
  // Pack fired while drawer unmapped → honest HOLD (surface-noun bypass kill).
  return buildUnmappedConceptHoldBootstrap(query, {
    drawer_id: "unmapped_hold",
    suggested_topic_class: "pack_bypass_when_drawer_unmapped",
  });
}

/** Core routing — Arm A xref shrink applied by exported wrapper. */
function buildTopicalFreeformBootstrapCore(query: string): TopicalFreeformBootstrap | null {
  const offtopic = classifyProductRiskOfftopic(query);
  if (offtopic) {
    return {
      preset_id: FREEFORM_OFFTOPIC_PRESET_ID,
      query_mode: "inquiry_offtopic_redirect",
      answer: buildOfftopicRedirectAnswerKo(query, offtopic),
      verse_refs: [],
      one_liner_ko: OFFTOPIC_REDIRECT_COPY[offtopic].title,
      gap_ko: OFFTOPIC_REDIRECT_COPY[offtopic].body,
      governance: `[HYPO][NON_GATING] · send_gate: HOLD · ${FREEFORM_OFFTOPIC_BANNER_KO}`,
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_OFFTOPIC_BANNER_KO,
      offtopic_class: offtopic,
    };
  }

  // Matching abstain HOLD=[] — personalize 사주 (before divination noun-domain pack).
  // Gate0 af_gold_32: 「제 사주에 맞는 성경 구절」≠ research 「성경에서 사주…어떻게」
  if (detectMatchingAbstainHold(query)) {
    const qShort = query.trim().slice(0, 96);
    return {
      preset_id: FREEFORM_OFFTOPIC_PRESET_ID,
      query_mode: "inquiry_matching_abstain_hold",
      answer: [
        `「${qShort}」→ MATCHING ABSTAIN · HOLD=[]`,
        "",
        "개인 사주·운세에 맞춘 구절 추천은 매칭층에서 보류합니다.",
        "「성경에서 점술·사주를 어떻게 다루는가」 연구 질문은 별도 주제 팩을 씁니다.",
        "",
        "### 한계",
        `- ${FREEFORM_OFFTOPIC_BANNER_KO}`,
        "- [HYPO][NON_GATING] · send_gate: HOLD · 개인 점술·운세 확정 아님",
      ].join("\n"),
      verse_refs: [],
      one_liner_ko: "개인 사주 맞춤 구절 · 매칭 HOLD=[]",
      gap_ko: "개인화 점술 요청은 앵커를 반환하지 않습니다. 연구 질문으로 바꿔 주세요.",
      governance: `[HYPO][NON_GATING] · send_gate: HOLD · matching_abstain · ${FREEFORM_OFFTOPIC_BANNER_KO}`,
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_OFFTOPIC_BANNER_KO,
      drawer_id: "personalize_abstain",
      drawer_pack_bound: true,
    };
  }

  // John 3:16 hub — before bare ref-explicit (citation family + school parallel).
  if (
    detectJohn316Topic(query) ||
    matchGoldenHubQuery(query)?.hub_id === "john316_salvation"
  ) {
    const verse_refs = resolveJohn316SalvationPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_john316",
      answer: buildJohn316ThematicAnswerKo(query),
      verse_refs,
      one_liner_ko: "요한복음 3:16 · 3:17 · 로마서 5:8 — 사랑·구원 언어 · 단정 금지",
      gap_ko:
        "세상·영생 범위는 학파 병렬로 읽습니다. 단일 교리·구원 조건 확정은 하지 않습니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectSalvationAssuranceTopic(query)) {
    const verse_refs = resolveSalvationAssurancePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_salvation_assurance",
      answer: buildSalvationAssuranceThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "구원보장 — John.10.28 · Rom.8.38 · 1John.5.13 병렬 [HYPO] · 교파 단정 없음",
      gap_ko:
        "구원 보장 vs 상실 가능은 학파 병렬만 · universalism·교파 확정 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectBaptismPracticeTopic(query)) {
    const verse_refs = resolveBaptismPracticePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_baptism_practice",
      answer: buildBaptismPracticeThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "세례 실천 — Matt.28.19 · Rom.6.3–4 · 1Pet.3.21 softpack [HYPO]",
      gap_ko: "세례=구원 필수 공식 단정 금지 · salvation_assurance와 분기.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectLordsSupperTopic(query)) {
    const verse_refs = resolveLordsSupperPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_lords_supper",
      answer: buildLordsSupperThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "성찬 — Matt.26.26 · 1Cor.11.24–26 softpack [HYPO]",
      gap_ko: "실재/상징 단일 판결 금지 · 세례 FAQ와 합선 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectPassionCrownTopic(query)) {
    const verse_refs = resolvePassionCrownPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_passion_crown",
      answer: buildPassionCrownThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "가시면류관 — Matt.27.29 · Mark.15.17 · John.19.2 softpack [HYPO]",
      gap_ko: "가시면류관 질문인데 G3 unmapped HOLD·일반팩만이면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectGen2EveCreationTopic(query)) {
    const verse_refs = resolveGen2EveCreationPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_gen2_eve_creation",
      answer: buildGen2EveCreationThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "Gen.2 하와·갈비뼈 — Gen.2.21–24 citation lock [HYPO]",
      gap_ko: "가인 아내·네피림·결혼 FAQ와 합선 금지 · unmapped HOLD 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectMaryIntercessionTopic(query)) {
    const verse_refs = resolveMaryIntercessionPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_mary_intercession",
      answer: buildMaryIntercessionThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "마리아·중보 — Luke.1 · John.19 · 1Tim.2.5 softpack [HYPO]",
      gap_ko: "일반 주기도 팩으로 마리아 FAQ를 대체하면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectGoodSamaritanTopic(query)) {
    const verse_refs = resolveGoodSamaritanPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_good_samaritan",
      answer: buildGoodSamaritanThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko: "선한 사마리아인 — Luke.10.33–37 citation lock [HYPO]",
      gap_ko: "비유 FAQ인데 unmapped HOLD면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectProdigalSonTopic(query)) {
    const verse_refs = resolveProdigalSonPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_prodigal_son",
      answer: buildProdigalSonThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko: "탕자 비유 — Luke.15.20–32 citation lock [HYPO]",
      gap_ko: "탕자 FAQ인데 unmapped HOLD면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectIsaiah53Topic(query)) {
    const verse_refs = resolveIsaiah53PrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_isaiah53",
      answer: buildIsaiah53ThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko: "이사야 53 고난의 종 — Isa.53 · 1Pet.2.24 [HYPO]",
      gap_ko: "Isa.53 FAQ인데 unmapped HOLD면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectBeatitudesTopic(query)) {
    const verse_refs = resolveBeatitudesPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_beatitudes",
      answer: buildBeatitudesThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko: "산상수훈·팔복 — Matt.5 · Luke.6 citation lock [HYPO]",
      gap_ko: "팔복 FAQ인데 unmapped HOLD면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectWomenPastorsChurchOfficeTopic(query)) {
    const verse_refs = resolveWomenPastorsChurchOfficePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_women_pastors_church_office",
      answer: buildWomenPastorsChurchOfficeThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "여성 목사·직분 — 1Tim.2.12 · Gal.3.28 · Rom.16.1 softpack [HYPO]",
      gap_ko: "안수 판결·문화전쟁 처방 금지 · 성찬/방언과 합선 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectScriptureReliabilityTopic(query)) {
    const verse_refs = resolveScriptureReliabilityPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_scripture_reliability",
      answer: buildScriptureReliabilityThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "성경 신뢰·정경 — 2Tim.3.16 · Ps.119.105 · Heb.4.12 softpack [HYPO]",
      gap_ko: "FAQ 본문 복제·역본 재판·모순=불신 단정 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "scripture_word",
      drawer_pack_bound: true,
    };
  }

  if (detectSexualityPurityEthicsTopic(query)) {
    const verse_refs = resolveSexualityPurityEthicsPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_sexuality_purity_ethics",
      answer: buildSexualityPurityEthicsThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "몸·성 윤리 soft — 1Cor.6 · 1Thess.4 · Heb.13.4 [HYPO]",
      gap_ko: "죄 판결·법률·강제 교정 Final Action 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "sexuality_purity",
      drawer_pack_bound: true,
    };
  }

  if (detectDeathFuneralHopeTopic(query)) {
    const verse_refs = resolveDeathFuneralHopePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_death_funeral_hope",
      answer: buildDeathFuneralHopeThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "죽음·장례·천국 — John.11.25 · 1Cor.15.55 · Rev.21.4 softpack [HYPO]",
      gap_ko:
        "장례·사후 질문인데 Job/적그리스도 팩으로 대체하지 않습니다 · 자살 처방 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectDatingPartnerCharacterTopic(query)) {
    const verse_refs = resolveDatingPartnerCharacterPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_dating_partner_character",
      answer: buildDatingPartnerCharacterThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "연애 상대 성품 — Prov.31.30 · 2Cor.6.14 · 1Cor.13.4 softpack [HYPO]",
      gap_ko: "궁합·사주·타로·연애운·시기 점 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "family_marriage",
      drawer_pack_bound: true,
    };
  }

  if (detectIllnessComfortHealingTopic(query)) {
    const verse_refs = resolveIllnessComfortHealingPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_illness_comfort_healing",
      answer: buildIllnessComfortHealingThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "병중 위로 — Ps.103.3 · Jas.5.14 · Mark.5.34 softpack [HYPO]",
      gap_ko: "치료 보장·병원 거부·의료 대체 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "healing_sickness",
      drawer_pack_bound: true,
    };
  }

  if (detectWorkplaceAnxietyFearTopic(query)) {
    const verse_refs = resolveWorkplaceAnxietyFearPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_workplace_anxiety_fear",
      answer: buildWorkplaceAnxietyFearThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "직장 불안 — Phil.4.6 · Matt.6.34 · 1Pet.5.7 softpack [HYPO]",
      gap_ko: "직장운·사주·타로·임상 대체 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "fear_anxiety",
      drawer_pack_bound: true,
    };
  }

  if (detectTemptationSpiritualWarfareTopic(query)) {
    const verse_refs = resolveTemptationSpiritualWarfarePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_temptation_spiritual_warfare",
      answer: buildTemptationSpiritualWarfareThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "시험·유혹 — 1Cor.10.13 · Matt.4.1 · Eph.6.11 softpack [HYPO]",
      gap_ko: "사주·중독 처방 금지 · 절주 질문은 temperance.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "temptation_spiritual_warfare",
      drawer_pack_bound: true,
    };
  }

  if (detectCreationEvolutionDialogueTopic(query)) {
    const verse_refs = resolveCreationEvolutionDialoguePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_creation_evolution_dialogue",
      answer: buildCreationEvolutionDialogueThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "신앙·진화 대화 — Gen.1 · Heb.11.3 · Col.1.16 softpack [HYPO]",
      gap_ko: "과학 연대·진화 메커니즘·교파 공식 단정 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "creation_origins",
      drawer_pack_bound: true,
    };
  }

  if (detectFamilyMarriageTopic(query)) {
    const verse_refs = resolveFamilyMarriagePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_family_marriage",
      answer: buildFamilyMarriageThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "가정·결혼 — Gen.2.24 · Eph.5.25 · Matt.19.5 softpack [HYPO]",
      gap_ko:
        "연애 궁합·시기 점·사주 합선 금지 · 부모-자녀 팩으로 부부 질문 대체 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "family_marriage",
      drawer_pack_bound: true,
    };
  }

  if (detectForgivenessGraceTopic(query)) {
    const verse_refs = resolveForgivenessGracePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_forgiveness_grace",
      answer: buildForgivenessGraceThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "용서·은혜 — Matt.6.14 · Eph.4.32 · Col.3.13 softpack [HYPO]",
      gap_ko: "학대 방조·화해 강제 단정 금지 · 죄책 전용 팩 대체 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "forgiveness_grace",
      drawer_pack_bound: true,
    };
  }

  if (detectHolySpiritBasicsTopic(query)) {
    const verse_refs = resolveHolySpiritBasicsPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_holy_spirit",
      answer: buildHolySpiritBasicsThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "성령 — John.14.26 · Gal.5.22 · Acts.1.8 softpack [HYPO]",
      gap_ko: "방언 필수·은사 시험 단정 금지 · 신앙 일반팩 대체 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "holy_spirit",
      drawer_pack_bound: true,
    };
  }

  if (detectRevelationInterpretiveCautionTopic(query)) {
    const verse_refs = resolveRevelationInterpretiveCautionPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_revelation_interpretive_caution",
      answer: buildRevelationInterpretiveCautionThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "계시록 해석 주의 — Rev.1.3 · Matt.24.36 · 2Pet.1.20 [HYPO]",
      gap_ko: "날짜·인물 1:1 해독 금지 · 666은 antichrist 허브로 분기.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectGreatCommissionTopic(query)) {
    const verse_refs = resolveGreatCommissionPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_mission_evangelism",
      answer: buildGreatCommissionThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "지상명령 — Matt.28.19 · Acts.1.8 · 1Pet.3.15 softpack [HYPO]",
      gap_ko: "문화전쟁·강제 개종 단정 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "mission_evangelism",
      drawer_pack_bound: true,
    };
  }

  if (detectJesusCamePurposeTopic(query)) {
    const verse_refs = resolveJesusCamePurposePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_jesus_came_purpose",
      answer: buildJesusCamePurposeThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "왜 오셨는가 — Luke.19.10 · John.3.16 · 1Tim.1.15 softpack [HYPO]",
      gap_ko: "종말 날짜·교파 공식 단정 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "jesus_person_work",
      drawer_pack_bound: true,
    };
  }

  if (detectCreationSevenDaysTopic(query)) {
    const verse_refs = resolveCreationSevenDaysPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_creation_seven_days",
      answer: buildCreationSevenDaysThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "7일 창조 — Gen.1 · Exod.20.11 · Heb.4.4 softpack [HYPO]",
      gap_ko: "지구 나이·지질 연대 단정 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "creation_origins",
      drawer_pack_bound: true,
    };
  }

  if (detectHonestyIntegrityTopic(query)) {
    const verse_refs = resolveHonestyIntegrityPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_honesty_integrity",
      answer: buildHonestyIntegrityThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "정직·성실 — Prov.12.22 · Eph.4.25 · Ps.15.2 softpack [HYPO]",
      gap_ko: "법률·위증 조언 금지 · speech_guard 얇은 대체 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "speech_truth",
      drawer_pack_bound: true,
    };
  }

  if (detectAdolescenceParentingTopic(query)) {
    const verse_refs = resolveAdolescenceParentingPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_adolescence_parenting",
      answer: buildAdolescenceParentingThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "사춘기 양육 — Prov.22.6 · Deut.6 · Eph.6.4 softpack [HYPO]",
      gap_ko: "의료·체벌·성적 처방 금지 · 얇은 intent parenting 대체 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  if (detectWatchfulnessParousiaTopic(query)) {
    const verse_refs = resolveWatchfulnessParousiaPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_watchfulness_parousia",
      answer: buildWatchfulnessParousiaThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "깨어있음·재림 소망 — Matt.24.42 · 1Thess.5.6 softpack [HYPO]",
      gap_ko: "재림·휴거 날짜/연도 단정 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "prophecy_hope_watchfulness",
      drawer_pack_bound: true,
    };
  }

  if (detectTemperanceAbstinenceTopic(query)) {
    const verse_refs = resolveTemperanceAbstinencePrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_temperance_abstinence",
      answer: buildTemperanceAbstinenceThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "절제·절주 — Prov.20.1 · Eph.5.18 · Rom.14.21 softpack [HYPO]",
      gap_ko: "의료·재활 처방 금지 · 유혹 일반팩으로 절주 질문 대체 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "temperance_abstinence",
      drawer_pack_bound: true,
    };
  }

  // Explicit KO cite 「N장 M절」— before drawer/noun packs (batch6 b6_01 class).
  {
    const hit = parseKoRefExplicitV1(query);
    if (hit) {
      const qShort = query.trim().slice(0, 96);
      const verse_refs = hit.refs;
      return {
        preset_id: FREEFORM_TOPICAL_PRESET_ID,
        query_mode: "inquiry_ref_explicit_ko_cite",
        answer: [
          `「${qShort}」— 명시 장절 인용 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
          "",
          "### 본문 앵커 (ref-explicit)",
          `${verse_refs.join(" · ")}을 1차 좌표로 둡니다.`,
          "- 질문 문장에 권·장·절이 직접 있으므로 generic theology soft pack으로 대체하지 않습니다.",
          "- 해석·학파 분기는 병렬로만 두고 단정하지 않습니다.",
          "",
          "### 한계",
          "- 연구 참고 · 교리·과학·투자 확정 아님.",
        ].join("\n"),
        verse_refs,
        one_liner_ko: `ref-explicit — ${verse_refs[0]} citation lock [HYPO]`,
        gap_ko: "명시 구절 질문입니다. generic theology soft pack으로 대체하지 않습니다.",
        governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
        citation_strength: "soft",
        honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
        drawer_id: "scripture_word",
        drawer_pack_bound: true,
      };
    }
  }

  // Allusion: Gen.3 Eve/serpent (before generic temptation pack).
  if (/선악과|하와.{0,24}뱀|뱀.{0,24}(?:유혹|하와)|에덴.{0,12}뱀/i.test(query)) {
    const verse_refs = ["Gen.3.1", "Gen.3.4", "Gen.3.6", "2Cor.11.3"];
    const qShort = query.trim().slice(0, 96);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_gen3_fall_allusion",
      answer: [
        `「${qShort}」— 창세기 3장(하와·뱀·선악과) 암시 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (allusion · Gen.3)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- 일반 유혹 팩(마 4장 계열)만으로 창세기 3장 질문을 대체하면 topic-fitness FAIL입니다.",
        "",
        "### 한계",
        "- 연구 참고 · 교리 단정 아님.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "Gen.3 allusion — Gen.3.1–6 · 2Cor.11.3 [HYPO]",
      gap_ko: "하와·뱀·선악과 암시인데 일반 유혹팩만이면 FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "temptation_spiritual_warfare",
      drawer_pack_bound: true,
    };
  }

  // Allusion: Matt.6.25 먹을까 입을까.
  if (/무엇을\s*먹을까|입을까\s*염려|먹을까\s*입을까/i.test(query)) {
    const verse_refs = ["Matt.6.25", "Matt.6.31", "Matt.6.33", "Matt.6.34"];
    const qShort = query.trim().slice(0, 96);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_matt6_anxiety_allusion",
      answer: [
        `「${qShort}」— 마태복음 6장(먹을까 입을까) 암시 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (allusion · Matt.6)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- 일반 담대 팩만 채우고 Matt.6.25–34를 빼면 allusion_miss입니다.",
        "",
        "### 한계",
        "- 연구 참고 · 재정 확정·투자 조언 아님.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "Matt.6 allusion — Matt.6.25–34 [HYPO]",
      gap_ko: "먹을까 입을까 암시인데 Matt.6 직격이 없으면 FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "fear_anxiety",
      drawer_pack_bound: true,
    };
  }

  // Gematria / math-original — before drawer/unmapped swallow (friend battery G1 pin).
  if (detectGematriaMeaningFreeformTopic(query)) {
    const verse_refs = resolveResearchTheologyPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_gematria_freeform",
      answer: buildResearchTheologyThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "게마트리아·원어 수학화 — 학파 병렬 · 단일 해독·존재 단정 없음 [HYPO]",
      gap_ko:
        "게마트리아/ELS는 현대 주장층입니다. 숫자→의미 단정·666 인물 대응·예언 해독은 하지 않습니다.",
      governance: `[HYPO][NON_GATING] · send_gate: HOLD · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  // Drawer taxonomy v1 — remaining L2 soft packs, then known-without-pack HOLD.
  {
    const drawer = resolveAskDrawerV1(query);
    const remL2 = tryBuildRemainingDrawerL2Bootstrap(query, drawer);
    if (remL2) {
      return remL2 as TopicalFreeformBootstrap;
    }
    if (isDrawerKnownWithoutPack(drawer)) {
      return buildUnmappedConceptHoldBootstrap(query, {
        drawer_id: drawer.drawer_id,
        suggested_topic_class: drawer.drawer_id,
      });
    }
  }

  // BIB-DYN primary: geo/nation/future OR fixture needle hit — before G3 softmatch essays.
  const bibDynPacket = matchBibDynPatternForAskPrimary(query);
  if (bibDynPacket) {
    const verse_refs = extractBibDynPatternVerseRefs(bibDynPacket);
    const rejected = bibDynPacket.gate_status === "REJECTED_INTENT";
    const passed =
      bibDynPacket.gate_status === "PASSED" &&
      (bibDynPacket.top_matches || []).length > 0;
    if (rejected || passed || bibDynPacket.gate_status.startsWith("REJECTED")) {
      return {
        preset_id: BIB_DYN_ASK_PRIMARY_PRESET_ID,
        query_mode: BIB_DYN_ASK_PRIMARY_QUERY_MODE,
        answer: buildBibDynPrimaryAnswerKo(bibDynPacket, query),
        verse_refs,
        one_liner_ko: rejected
          ? "BIB-DYN · 의도 거절 (매매·예측 금지)"
          : passed
            ? "BIB-DYN · 성경 서사 패턴 연구 (예보 아님)"
            : "BIB-DYN · 패턴 미매칭 HOLD",
        gap_ko: rejected
          ? "매매·예측 신호 의도는 패턴 연구 레인에서 거절합니다."
          : passed
            ? "문헌 축 패턴·국면 어휘만 · 현대 국가 일정 예보 금지 · track_a_bridge=false"
            : "패턴 코사인/니들이 약합니다. 구절·모티프로 좁혀 주세요.",
        governance: `[HYPO][NON_GATING] · send_gate: HOLD · research_only · prediction_claims=forbidden · track_a_bridge=false · ${BIB_DYN_PRIMARY_BANNER_KO}`,
        citation_strength: verse_refs.length > 0 ? "soft" : "soft",
        honest_control_banner_ko: BIB_DYN_PRIMARY_BANNER_KO,
        bib_dyn_primary: true,
      };
    }
  }

  // Ultra-short faith tokens (믿음/부활… / 신앙이란) — before length floors blank them.
  if (isShortFaithTokenInquiry(query)) {
    if (isShortFaithSoftRoute(query)) {
      const verse_refs = resolveBiblicalFaithPrimaryRefs(query);
      return {
        preset_id: FREEFORM_TOPICAL_PRESET_ID,
        query_mode: "inquiry_thematic_faith_freeform",
        answer: buildBiblicalFaithThematicAnswerKo(query, verse_refs),
        verse_refs,
        one_liner_ko:
          "짧은 신앙 토큰 — Heb.11 / John.3.16 병렬 [HYPO] · 단정 교리 없음",
        gap_ko:
          "한두 단어 질문입니다. 학파 분기·약한 앵커만 제시하며 ‘반드시’ 판결은 하지 않습니다.",
        governance: "[HYPO][NON_GATING] · send_gate: HOLD",
        citation_strength: "soft",
        honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      };
    }
    const verse_refs = resolveResearchTheologyPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_research_theology_freeform",
      answer: buildResearchTheologyThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "짧은 복음/부활 토큰 — soft citation · grade:general · 허브 강제 없음",
      gap_ko:
        "한두 단어 질문입니다. 큐레이션 팩·학자모드 가장 없이 약한 연구 앵커만 제시합니다.",
      governance: `[HYPO][NON_GATING] · send_gate: HOLD · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // antichrist_666 / 666 person-decode dogma — before G3/life floors (hub SSOT).
  if (detectAntichrist666FreeformTopic(query)) {
    const verse_refs = resolveAntichrist666FreeformPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: FREEFORM_ANTICHRIST_666_QUERY_MODE,
      answer: buildAntichrist666FreeformAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "666·적그리스도 — 학파 병렬 · 단일 인물 해독 거부 [HYPO][NON_GATING]",
      gap_ko:
        "짐승의 수와「이미 많은 적그리스도」는 공동체 경계·상징 해석 축이며 특정 인물·날짜 1:1 단정은 하지 않습니다. Rev.21 새하늘 팩과 합선하지 않습니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // Noun-domain: 성막/tabernacle before bare faith/soteriology pack swallow.
  if (detectTabernacleNounDomainQuery(query)) {
    const verse_refs = resolveTabernacleNounDomainPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_tabernacle_noun_domain",
      answer: buildTabernacleNounDomainThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "성막 noun-domain — Exod 25–40 · Heb 9 ≥1 필수 · 구원 유추는 병렬 [HYPO]",
      gap_ko:
        "성막 질문인데 구원 일반 팩(Rom.10.9 등)만 채우면 noun-domain coverage FAIL입니다. 유형론은 학파 병렬·단정 금지.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // 점술·사주·관상·타로 — before generic Deut.4.2 theology soft pack.
  if (
    detectDivinationRefusalTopic(query) &&
    (isResearchTheologyFreeformInquiry(query) || matchGoldenHubQuery(query)?.hub_id === "divination_refusal")
  ) {
    const verse_refs = resolveDivinationRefusalPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_divination_refusal",
      answer: buildDivinationRefusalThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "점술 refusal wall — Deut.18.10 · Lev.19 · Isa.47 · Acts.16 ≥1 · 운세 execution 금지",
      gap_ko:
        "점술 질문인데 Deut.4.2/John.5.39/Rev.13.18 일반팩만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // 시편 23 — before faith/generic pack swallow (parity with studio curated path).
  // Friend battery ps23_seed: stamp topic_ps_23_anchor (G0) — not dynamic_topical_freeform (G1).
  // qa_presets slim catalog may omit the row; freeform early/late still carries the G0 seed id.
  if (detectPsalm23Topic(query)) {
    const verse_refs = [...PSALM23_SHEPHERD_FREEFORM_PRIMARY_REFS];
    return {
      preset_id: "topic_ps_23_anchor",
      query_mode: "inquiry_thematic_psalm23",
      answer: buildPsalm23ShepherdThematicAnswerKo(query),
      verse_refs,
      one_liner_ko: "시편 23 — 목자·골짜기·회복 (시편 23:1 · 23:4 · 23:5 · 23:6)",
      gap_ko: "시편 23 질문인데 일반 상고팩(Deut.4.2…)만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      // Strong citation family (Ps.23.*) — avoid soft banner so control grade stays G0.
      citation_strength: "strong",
      honest_control_banner_ko: null,
    };
  }
  // 욥기 고난 — before G3 empty-ref HOLD.
  if (detectJobSufferingTopic(query)) {
    const verse_refs = [...JOB_SUFFERING_FREEFORM_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_job",
      answer: buildJobSufferingThematicAnswerKo(query),
      verse_refs,
      one_liner_ko: "욥기 고난 — Job.1 · Job.42 citation lock [HYPO]",
      gap_ko: "욥기 질문인데 G3 no-citation 또는 일반팩만이면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // 중보/위해 기도 — before broad prayer pack (batch2 af_gold_16).
  if (detectIntercessionPrayerTopic(query)) {
    const verse_refs = [...INTERCESSION_PRAYER_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_intercession_noun_domain",
      answer: [
        `「${query.trim().slice(0, 96)}」— 중보·타인을 위한 기도 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · intercession)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- **디모데전서 2.1:** 모든 사람을 위하여 간구·기도·도고·감사를 하라.",
        "- **욥기 42.10 / 야고보 5.16 / 에베소 6.18:** 타인을 위한 중보·서로 기도 축.",
        "",
        "### 한계·주의",
        "- 본 답은 연구 참고이며 응답·치유 확정이 아닙니다.",
        "- 일반 기도팩(주기도만)으로 중보 질문을 대체하면 topic-fitness FAIL입니다.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "intercession — 1Tim.2.1 · Job.42.10 · Jas.5.16 citation lock [HYPO]",
      gap_ko: "중보 질문인데 일반 기도/신앙팩만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // 기도 noun-domain — before bare faith pack (Heb.11 / John.3.16) swallow.
  if (detectPrayerTopicQuery(query)) {
    const verse_refs = [...RESEARCH_THEOLOGY_PRAYER_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_prayer_noun_domain",
      answer: buildPrayerNounDomainThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko: "기도 noun-domain — Matt.6 · 1Thess.5.17 · Phil.4.6 ≥1 필수",
      gap_ko: "기도 질문인데 신앙 일반팩(Heb.11/John.3.16)만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // Comfort · presence (힘들 때 / 곁에) — before faith pack (Gate0 af_gold_09).
  if (detectComfortPresenceTopic(query)) {
    const verse_refs = [...COMFORT_PRESENCE_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_comfort_presence",
      answer: [
        `「${query.trim().slice(0, 96)}」— 힘듦·임재(곁에 계심) 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · comfort presence)",
        `${verse_refs.slice(0, 6).join(" · ")}을 후보 좌표로 둡니다.`,
        "- **이사야 41.10:** 두려워 말라 · 내가 너와 함께 함 — 임재·담대 축.",
        "- **시편 23.4:** 사망의 음침한 골짜기에서도 — 목자 동행.",
        "- **신명기 31.6 / 히브리서 13.5:** 떠나지 아니하리라 약속 축.",
        "",
        "### 한계·주의",
        "- 본 답은 연구 참고이며 상담·치유·운세 확정이 아닙니다.",
        "- 신앙 일반팩(Heb.11/John.3.16)만으로 이 질문을 채우면 topic-fitness FAIL입니다.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "comfort presence — Isa.41.10 · Ps.23.4 · Deut.31.6 citation lock [HYPO]",
      gap_ko: "임재·담대 질문인데 신앙 일반팩만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // Comfort · sorrow (슬픔 / 위로 / 상실·원망) — before faith / generic (Gate0 af_gold_10 · soft_grief).
  if (detectComfortSorrowTopic(query)) {
    const verse_refs = [...COMFORT_SORROW_PRIMARY_REFS];
    const qShort = query.trim().slice(0, 96);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_comfort_sorrow",
      answer: [
        `「${qShort}」— 상실과 원망이 섞인 질문은, 성급히 ‘믿어라’로 덮지 않고 탄식의 언어부터 함께 두는 것이 맞습니다.`,
        "",
        "### 짧은 공감",
        "가족을 잃고 하나님이 원망스러운 마음은 신앙 밖이 아닙니다. 성경에도 울분·항의·침묵을 하나님 앞에 쏟아 놓은 탄식의 자리가 있습니다. 지금은 ‘정답 문장’보다, 그 고통을 부정하지 않는 본문을 붙잡는 편이 안전합니다.",
        "",
        "### 본문 앵커 (탄식 · 위로 · 임재)",
        `${verse_refs.slice(0, 7).join(" · ")}`,
        "- **시편 13.1 / 22.1:** ‘언제까지… 버리시나이까’ · ‘어찌하여 나를 버리셨나이까’ — 원망·버림받음 느낌도 기도로 올려질 수 있음을 보여 줍니다.",
        "- **욥기 3.11:** 고난 앞에서 말문이 막히고 항변하는 인간 — 성급한 교훈보다 탄식 자체가 본문입니다.",
        "- **시편 34.18 / 마태 5.4:** 마음이 상한 자 · 애통하는 자에게 가까이 오시는 하나님 · 복.",
        "- **고린도후서 1.3–4 / 마태 11.28:** 위로의 하나님 · 무거운 짐 진 자를 부르심 — 강제 낙관이 아닌 초대.",
        "",
        "### 한계·주의",
        "- 본 답은 성경 연구 참고이며, 상담·심리치료·목회 케어를 대체하지 않습니다.",
        "- 위기·자해 위험이 있으면 가까운 사람·전문 기관·긴급 도움을 우선하세요.",
        "- 단일 교리 판결·‘원망하지 말라’ 처방·운세형 확정은 하지 않습니다.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "comfort sorrow — Ps.13/22 lament · Job · 2Cor.1 · Ps.34 soft pastoral [HYPO]",
      gap_ko: "상실·원망 질문에 공감·탄식 본문 없이 G3 HOLD만 내면 pastoral FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  // Queue→map packs (batch2 commander_frozen families) — before topical/generic swallow.
  if (detectGuiltForgivenessTopic(query)) {
    const verse_refs = [...GUILT_FORGIVENESS_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_guilt_forgiveness",
      answer: [
        `「${query.trim().slice(0, 96)}」— 죄책·용서 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · guilt/forgiveness)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- **요한일서 1.9:** 죄를 자백하면 사하시며 깨끗하게 하심.",
        "- **로마 8.1 / 시편 103.12:** 정죄 없음 · 동쪽에서 서쪽처럼 옮기심.",
        "",
        "### 한계·주의",
        "- 본 답은 연구 참고이며 상담·치유 확정이 아닙니다.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "guilt/forgiveness — 1John.1.9 · Rom.8.1 · Ps.103.12 citation lock [HYPO]",
      gap_ko: "죄책 질문인데 신앙 일반팩만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  if (detectRepentanceTopic(query)) {
    const verse_refs = [...REPENTANCE_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_repentance",
      answer: [
        `「${query.trim().slice(0, 96)}」— 회개 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · repentance)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- **사도행전 3.19:** 회개하고 돌이켜 죄 없이함을 받으라.",
        "- **고린도후서 7.10 / 누가 15.7:** 하나님의 뜻대로 하는 근심 · 하늘에서의 기쁨.",
        "",
        "### 한계·주의",
        "- 본 답은 연구 참고이며 교리·구원 확정이 아닙니다.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "repentance — Acts.3.19 · 2Cor.7.10 · Luke.15.7 citation lock [HYPO]",
      gap_ko: "회개 질문인데 신앙 일반팩만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  if (detectLoveEnemyTopic(query)) {
    const verse_refs = [...LOVE_ENEMY_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_love_enemy",
      answer: [
        `「${query.trim().slice(0, 96)}」— 원수 사랑 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · love enemy)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- **마태 5.44:** 원수를 사랑하며 박해하는 자를 위하여 기도하라.",
        "- **로마 12.20 / 누가 6.27:** 원수에게 먹을 것을 · 너희를 미워하는 자를 선대하라.",
        "",
        "### 한계·주의",
        "- 본 답은 연구 참고이며 관계·법률 확정이 아닙니다.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "love-enemy — Matt.5.44 · Rom.12.20 · Luke.6.27 citation lock [HYPO]",
      gap_ko: "원수 사랑 질문인데 일반/신앙팩만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  if (detectWealthStewardshipTopic(query)) {
    const verse_refs = [...WEALTH_STEWARDSHIP_PRIMARY_REFS];
    const qShort = query.trim().slice(0, 96) || "이 질문";
    const refLine = verse_refs.slice(0, 6).join(" · ");
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_wealth_stewardship",
      answer: [
        `[HYPO] 질문: ${qShort}`,
        "",
        "### 짧은 직접 답",
        "**재물·십일조·도박·직업을 매수 추천·수익률·도박 가이드로 닫지 않습니다.** 탐심·마몬·청지기·나눔 언어를 학파 병렬로만 둡니다. [NON_GATING] · send_gate: HOLD",
        "",
        "### 근거 구절 (citation lock · wealth)",
        `${refLine}`,
        "- **디모데전서 6.10:** 돈을 사랑함이 일만 악의 뿌리 — ‘돈 자체’ vs ‘사랑함’ 독법 분기.",
        "- **마태 6.24 / 누가 12.15:** 하나님과 재물(마몬)을 겸하여 섬기지 못함 · 탐심을 조심하라.",
        "- **잠언 11.28 · 히브리서 13.5:** 부자를 의지하지 말라 · 돈을 사랑하지 말고 있는 바를 족한 줄로 알라.",
        "- **말라기 3.10:** 십일조·창고 — 신약 성도 의무 여부는 교파마다 갈림(단정 금지).",
        "",
        "### 학파·해석 병렬 (승자 고르지 않음)",
        "1. **청지기·나눔:** 소유를 위탁·나눔으로 읽는 전통 — 번영 복음 1:1 공식 아님.",
        "2. **마몬·충성 긴장:** Matt.6.24을 우상·충성 축으로 읽음 · 투자 금지 법률로 닫지 않음.",
        "3. **십일조·헌금:** Mal.3 · 신약 나눔 독법 병기 — ‘신약에도 의무인가’를 단일 교리로 판결하지 않음.",
        "4. **도박·탐심 윤리 FAQ:** ‘도박은 죄인가’·‘성경은 도박을’은 탐심·신속한 이득·청지기 언어로만 병기 — 도박 가이드·당첨 예언·로또 번호 금지.",
        "",
        "### 금지 1:1 / 반증",
        "- 비트코인·주식 매수 추천·수익률·코인 단타·도박 전략·당첨 번호 단정 금지.",
        "- 일반 상고팩(Deut/John.5.39)만으로 재물 질문을 대체하지 않습니다.",
        "- 십일조 미이행을 개인 저주·구원 상실로 판결하지 않습니다.",
        "- 도박=무조건 지옥 기계 판결·중독 임상 처방 금지.",
        "",
        "### 한계·주의",
        "연구 참고이며 투자·재테크·세무·법률 확정이 아닙니다. research_only · product_all_ok=false.",
        "",
        "### 다음 좁힌 질문 제안",
        "예: 「마몬(Matt.6.24) 읽기」, 「돈을 사랑함(1Tim.6.10)」, 「십일조 학파 병렬(연구)」, 「도박·탐심 경계(학파 병렬)」.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "wealth — 1Tim.6.10 · Matt.6.24 · Mal.3.10 · 도박윤리 densify [HYPO]",
      gap_ko: "재물 질문인데 일반 상고팩만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  if (detectSpeechGuardTopic(query)) {
    const verse_refs = [...SPEECH_GUARD_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_speech_guard",
      answer: [
        `「${query.trim().slice(0, 96)}」— 말·혀 절제 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · speech)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- **야고보 1.19:** 듣기는 속히 하고 말하기는 더디 하라.",
        "- **야고보 3.5 / 잠언 15.1:** 혀는 작은 지체 · 유순한 대답은 분노를 쉬게 함.",
        "",
        "### 한계·주의",
        "- 본 답은 연구 참고이며 상담·법률 확정이 아닙니다.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "speech — Jas.1.19 · Jas.3.5 · Prov.15.1 citation lock [HYPO]",
      gap_ko: "말조심 질문인데 unmapped/일반팩만이면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }
  if (detectHolySpiritTopic(query)) {
    const verse_refs = resolveHolySpiritBasicsPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_holy_spirit",
      answer: buildHolySpiritBasicsThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko: "holy_spirit — John.14.26 · Gal.5.22 · Acts.1.8 [HYPO]",
      gap_ko: "성령 질문인데 신앙 일반팩만 채우면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "holy_spirit",
      drawer_pack_bound: true,
    };
  }
  if (detectChurchFellowshipTopic(query)) {
    const verse_refs = [...CHURCH_FELLOWSHIP_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_church_fellowship",
      answer: [
        `「${query.trim().slice(0, 96)}」— 교회·교제 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · church)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- **사도행전 2.42 / 히브리서 10.25:** 교제·모이기를 폐하지 말며.",
        "- **고린도전서 12.12 / 에베소 4.4:** 한 몸·한 성령.",
        "",
        "### 한계·주의",
        "- 교단 비교·정치 처방 아님.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "church — Acts.2.42 · Heb.10.25 · 1Cor.12.12 [HYPO]",
      gap_ko: "교회 질문인데 일반팩만이면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "church_fellowship",
      drawer_pack_bound: true,
    };
  }
  if (detectWorshipThanksgivingTopic(query)) {
    const verse_refs = [...WORSHIP_THANKSGIVING_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_worship_thanksgiving",
      answer: [
        `「${query.trim().slice(0, 96)}」— 예배·감사 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · thanksgiving)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- **시편 100.4 / 95.1:** 감사함으로 그 문에 들어가며.",
        "- **요한 4.23 / 히브리서 13.15:** 신령과 진정·찬미의 제사.",
        "",
        "### 한계·주의",
        "- 교회론 전부 흡수하지 않음.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "thanksgiving — Ps.100.4 · Ps.95.1 · Heb.13.15 [HYPO]",
      gap_ko: "감사 질문인데 unmapped만이면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "worship_thanksgiving",
      drawer_pack_bound: true,
    };
  }
  if (detectPatienceTrialsTopic(query)) {
    const verse_refs = [...PATIENCE_TRIALS_PRIMARY_REFS];
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_patience_trials",
      answer: [
        `「${query.trim().slice(0, 96)}」— 인내·시련 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
        "",
        "### 본문 앵커 (citation lock · patience)",
        `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
        "- **야고보 1.2–3 / 로마 5.3–4:** 인내가 온전케 함 · 환난은 인내를.",
        "",
        "### 한계·주의",
        "- 욥기 전용 질문은 Job 팩을 씀 · 임상 트라우마 아님.",
      ].join("\n"),
      verse_refs,
      one_liner_ko: "patience — Jas.1.2 · Rom.5.3 · 1Pet.1.6 [HYPO]",
      gap_ko: "인내 질문인데 unmapped만이면 topic-fitness FAIL입니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      drawer_id: "suffering_trials",
      drawer_pack_bound: true,
    };
  }
  if (isTopicalFreeformInquiry(query)) {
    const verse_refs = resolveAiSocietySymbolismPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_topical_freeform",
      answer: buildAiSocietySymbolismThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "AI·사회·상징 — 형상/우상·지혜·짐승 후보 축 병렬 [HYPO] · 단일 해독 없음",
      gap_ko:
        "현대 AI는 본문 부재 주제입니다. 유형론·은유 후보만 제시하며 교리·투자·실거래 확정은 하지 않습니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  // Decalogue before generic/faith floors — honor-parents etc. must not be swallowed.
  const decalogueClass = resolveDecalogueQueryClassV1(query);
  if (decalogueClass) {
    const verse_refs = resolveDecaloguePrimaryRefs(decalogueClass, query);
    const query_mode = `inquiry_thematic_${decalogueClass}` as TopicalFreeformBootstrap["query_mode"];
    const oneLiners: Record<DecalogueQueryClassV1, string> = {
      decalogue_other_gods_freeform: "다른 신 금지 계명 — Exod/Deut/Isa 앵커 · 학파 병렬 [HYPO]",
      decalogue_idols_freeform: "우상 금지 계명 — Exod/Deut/Ps 앵커 · 학파 병렬 [HYPO]",
      decalogue_name_vain_freeform: "이름 헛되이 금지 — Exod/Deut/Matt 앵커 · 학파 병렬 [HYPO]",
      decalogue_sabbath_freeform: "안식일 계명 — Exod/Deut/Mark 앵커 · 학파 병렬 [HYPO]",
      decalogue_honor_parents_freeform: "부모 공경 계명 — Exod/Deut/Eph 앵커 · 학파 병렬 [HYPO]",
      decalogue_murder_freeform: "살인 금지 계명 — Exod/Deut/Matt/Rom 앵커 · 학파 병렬 [HYPO]",
      decalogue_adultery_freeform: "간음 금지 계명 — Exod/Deut/Matt 앵커 · 학파 병렬 [HYPO]",
      decalogue_steal_freeform: "도둑질 금지 계명 — Exod/Deut/Eph 앵커 · 학파 병렬 [HYPO]",
      decalogue_false_witness_freeform: "거짓 증거 금지 — Exod/Deut/Prov 앵커 · 학파 병렬 [HYPO]",
      decalogue_covet_freeform: "탐내 금지 계명 — Exod/Deut/Rom 앵커 · 학파 병렬 [HYPO]",
    };
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode,
      answer: buildDecalogueThematicAnswerKo(decalogueClass, query, verse_refs),
      verse_refs,
      one_liner_ko: oneLiners[decalogueClass],
      gap_ko:
        "GraphRAG·lemma bridge의 Dan/Job wrong-pack 대신 열계명 본문 축만 제시합니다. 교리·법률 확정 없음.",
      governance: `[HYPO][NON_GATING] · send_gate: HOLD · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  // Named John 3:16 — keep curated hub lane (belt if early hub path missed).
  if (
    detectJohn316Topic(query) ||
    matchGoldenHubQuery(query)?.hub_id === "john316_salvation"
  ) {
    const verse_refs = resolveJohn316SalvationPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_john316",
      answer: buildJohn316ThematicAnswerKo(query),
      verse_refs,
      one_liner_ko: "요한복음 3:16 · 3:17 · 로마서 5:8 — 사랑·구원 언어 · 단정 금지",
      gap_ko:
        "명시 구절 질문입니다. 세상·영생 범위는 학파 병렬로 읽으며 단일 교리 확정은 하지 않습니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  // Specialized research topics only (cross / angel / hell / bible-code …) — keep soft anchors.
  // Bible-code intentionally reuses RESEARCH_THEOLOGY_PRIMARY_REFS (soft pack) —
  // do not treat that as generic swallow → unmapped HOLD (friend battery residual).
  if (hasSpecializedResearchTopic(query)) {
    const verse_refs = resolveResearchTheologyPrimaryRefs(query);
    const bibleCode = isBibleCodeResearchTopic(query);
    if (!isDefaultGenericTheologySoftPack(verse_refs) || bibleCode) {
      return {
        preset_id: FREEFORM_TOPICAL_PRESET_ID,
        query_mode: "inquiry_thematic_research_theology_freeform",
        answer: buildResearchTheologyThematicAnswerKo(query, verse_refs),
        verse_refs,
        one_liner_ko: bibleCode
          ? "바이블 코드 — 존재 단정 없이 학파 병렬 [HYPO] · soft citation"
          : "특화 신학 주제 freeform — soft citation · [HYPO][NON_GATING]",
        gap_ko: bibleCode
          ? "바이블 코드/ELS는 현대 주장층입니다. 존재 증명·예언 해독·666 인물 대응은 하지 않습니다."
          : "특화 주제 앵커만 제시하며 교리·예언 확정은 하지 않습니다.",
        governance: `[HYPO][NON_GATING] · send_gate: HOLD · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
        citation_strength: "soft",
        honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      };
    }
  }

  // Narrow faith-definition only — 오배정 격하: broad FAITH_TOPIC swallow 금지.
  if (detectFaithCoreTopic(query) || isShortFaithTokenInquiry(query)) {
    if (isShortFaithSoftRoute(query) || detectFaithCoreTopic(query)) {
      const verse_refs = resolveBiblicalFaithPrimaryRefs(query);
      return {
        preset_id: FREEFORM_TOPICAL_PRESET_ID,
        query_mode: "inquiry_thematic_faith_freeform",
        answer: buildBiblicalFaithThematicAnswerKo(query, verse_refs),
        verse_refs,
        one_liner_ko:
          "신앙·믿음 정의 — 히브리서 11 · 요한복음 3:16 · 에베소·야고보 긴장 병렬 · 단정 교리 없음",
        gap_ko:
          "신앙 정의·의무는 학파·교파마다 분기합니다. 본문은 후보 앵커만 제시하며 ‘반드시’ 판결은 하지 않습니다.",
        governance: "[HYPO][NON_GATING] · send_gate: HOLD",
        citation_strength: "soft",
        honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
      };
    }
  }

  // Late drawer soft-pack fallback — matched drawer with L2 pack before unmapped HOLD.
  {
    const drawerLate = resolveAskDrawerV1(query);
    const softLate = tryBuildDrawerL2LateSoftBootstrap(query, drawerLate);
    if (softLate) {
      return softLate as TopicalFreeformBootstrap;
    }
  }

  // Stranger-life hobby softpack — before general-floor unmapped HOLD (G3 empty-ref).
  if (detectLifeWisdomHobbyTopic(query)) {
    const verse_refs = resolveLifeWisdomHobbyPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_life_wisdom_hobby",
      answer: buildLifeWisdomHobbyThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko:
        "취미·여가 — Eccl.3 · Prov.16.9 · Col.3.23 softpack [HYPO] · 처방 단정 없음",
      gap_ko:
        "취미 결정은 지혜·청지기 연구 축이며 ‘바꿔라/유지하라’ 교리·점술 처방이 아닙니다.",
      governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  // Layer-1 anti-fallback: would-be generic/faith/general swallow → unmapped HOLD + queue.
  // Friend battery bible_code: never collapse ELS/바이블코드 to unmapped HOLD (422 path).
  if (isBibleCodeResearchTopic(query)) {
    const verse_refs = resolveResearchTheologyPrimaryRefs(query);
    return {
      preset_id: FREEFORM_TOPICAL_PRESET_ID,
      query_mode: "inquiry_thematic_research_theology_freeform",
      answer: buildResearchTheologyThematicAnswerKo(query, verse_refs),
      verse_refs,
      one_liner_ko: "바이블 코드 — 존재 단정 없이 학파 병렬 [HYPO] · soft citation",
      gap_ko:
        "바이블 코드/ELS는 현대 주장층입니다. 존재 증명·예언 해독·666 인물 대응은 하지 않습니다.",
      governance: `[HYPO][NON_GATING] · send_gate: HOLD · ${FREEFORM_WEAK_CITATION_BANNER_KO}`,
      citation_strength: "soft",
      honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    };
  }

  // Wave11: Golden hub registry densify — before generic/faith unmapped HOLD.
  {
    const registryBoot = buildGoldenHubRegistryDensifyBootstrap(query);
    if (registryBoot) return registryBoot;
  }

  if (
    isBiblicalFaithFreeformInquiry(query) ||
    isResearchTheologyFreeformInquiry(query) ||
    isGeneralInquiryFreeformFloor(query) ||
    shouldDeferFaithPackToGeneral(query) ||
    isBareGospelAmbiguousQuery(query)
  ) {
    return buildUnmappedConceptHoldBootstrap(query);
  }

  // Bible/theology frame with no hand-routed pack → honest unmapped (af_gold_27 class).
  if (
    RESEARCH_THEOLOGY_FRAME_RE.test(query) ||
    TOPICAL_BIBLE_FRAME_RE.test(query) ||
    FAITH_TOPIC_RE.test(query)
  ) {
    return buildUnmappedConceptHoldBootstrap(query);
  }
  return null;
}

/** Topical freeform bootstrap — Arm A soft-drop+max_refs=6 applied when refs present. */
export function buildTopicalFreeformBootstrap(query: string): TopicalFreeformBootstrap | null {
  const boot = buildTopicalFreeformBootstrapCore(query);
  if (!boot) return null;
  return finalizeArmABootstrap(
    enforceUnmappedDrawerNoPackFireInvariant(query, boot),
  );
}
