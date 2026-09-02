/**
 * Logos Ask drawer router v1 — taxonomy classify → existing pack OR unmapped.
 *
 * Fixture SSOT (boundaries): docs/final/fixtures/logos_ask_drawer_taxonomy_v1.json
 * Commander freeze ACK 2026-08-10 · seed_refs NEVER loaded here.
 *
 * research_only · [NON_GATING] · send_gate HOLD · matching≠interpretation
 * pack_binding=null → honest unmapped_hold (queue with drawer id)
 */

import {
  normalizeAskQueryKoV1,
  pickUniqueLemmaDrawerV1,
} from "./logosAskDrawerLemmaNormalizeV1";

export type AskDrawerPackBinding =
  | "tabernacle"
  | "divination"
  | "prayer"
  | "intercession"
  | "guilt"
  | "repentance"
  | "comfort_presence"
  | "comfort_sorrow"
  | "wealth"
  | "speech"
  | "love_enemy"
  | "psalm23"
  | "job"
  | "patience"
  | "holy_spirit"
  | "church"
  | "thanksgiving"
  | "assurance"
  | "forgiveness"
  | "scripture"
  | "obedience"
  | "growth"
  | "temptation"
  | "temperance"
  | "healing"
  | "death_hope"
  | "service"
  | "mission"
  | "wisdom"
  | "work"
  | "justice"
  | "purity"
  | "god_character"
  | "prophecy_hope"
  | "faith_core"
  | "cross"
  | "angels"
  | "decalogue"
  | "family"
  | "creation"
  | "personalize_abstain"
  | null;

export type AskDrawerResolveV1 = {
  drawer_id: string;
  name_ko: string;
  matched: boolean;
  pack_binding: AskDrawerPackBinding;
  reason_ko: string;
  conflict_rule_id: string | null;
};

type DrawerRoute = {
  id_slug: string;
  name_ko: string;
  pack_binding: AskDrawerPackBinding;
  /** Keyword cues — not verse packs. */
  re: RegExp;
  weight: number;
};

/**
 * Frozen drawer cues (no seed_refs). Weight: higher wins; ties → unmapped_hold.
 * Terminals personalize_abstain / unmapped_hold handled by caller + fallback.
 */
const DRAWER_ROUTES: DrawerRoute[] = [
  {
    id_slug: "covenant_tabernacle_typology",
    name_ko: "언약·성막·유형",
    pack_binding: "tabernacle",
    re: /성막|성전\s*기물|일곱\s*가지\s*순서|유형론|tabernacle|성소/i,
    weight: 90,
  },
  {
    id_slug: "occult_divination_research",
    name_ko: "점술/주술 연구",
    pack_binding: "divination",
    re: /성경.{0,16}(?:점|사주|타로|점술)|(?:점술|신접|복술|점\s*치).{0,16}(?:성경|어떻게|말하|금지)|신접행위|divination|fortune[\s-]?tell/i,
    weight: 85,
  },
  {
    id_slug: "prayer",
    name_ko: "기도",
    pack_binding: "prayer",
    re: /어떻게\s*기도|기도해|주기도|간구|쉬지\s*말고\s*기도|기도(?:는|가|를|의|란|에)?.{0,12}(?:성경|응답|방법|의미)|bible.{0,20}pray/i,
    weight: 70,
  },
  {
    id_slug: "prayer",
    name_ko: "기도",
    pack_binding: "intercession",
    re: /위해\s*기도|중보|남을\s*위해\s*기도|다른\s*사람.{0,12}기도|intercess/i,
    weight: 88,
  },
  {
    id_slug: "sin_repentance",
    name_ko: "죄와 회개",
    pack_binding: "guilt",
    re: /죄책감|양심의\s*가책|양심이\s*괴로|괴로운\s*양심|죄책|용서받을\s*수|guilt/i,
    weight: 86,
  },
  {
    id_slug: "sin_repentance",
    name_ko: "죄와 회개",
    pack_binding: "repentance",
    re: /회개|돌이키|repent/i,
    weight: 84,
  },
  {
    id_slug: "fear_anxiety",
    name_ko: "두려움과 염려",
    pack_binding: "comfort_presence",
    re: /힘들\s*때|곁에\s*계신|두려워할\s*때|붙잡을\s*구절|임재|담대|불안할\s*때|염려|걱정/i,
    weight: 80,
  },
  {
    id_slug: "comfort_lament",
    name_ko: "위로와 탄식",
    pack_binding: "comfort_sorrow",
    re: /슬픔|위로가\s*되는|위로\s*말씀|슬플\s*때|애통|애도|상실|눈물|탄식|사별|별세|돌아가신|(?:가족|부모|아이|남편|아내|자식|사람).{0,12}잃|잃(?:고|어|은).{0,24}(?:가족|부모|아이|남편|아내|자식|사람)|하나님(?:이|께|을|한테)?.{0,16}원망|원망스러|grief|lament|bereave|mourn(?:ing)?|악몽|아이에게\s*읽어|읽어주면\s*좋은\s*말씀/i,
    weight: 82,
  },
  {
    id_slug: "assurance_peace",
    name_ko: "확신과 평안",
    pack_binding: "assurance",
    re: /구원\s*확신|정죄(?:감|가)?|평안이\s*없|assurance|no\s*condemnation|(?:구원|영생|정죄).{0,12}확신이\s*없|지옥.{0,20}무섭|지옥이?\s*두려|죽을\s*때.{0,24}지옥/i,
    weight: 83,
  },
  {
    id_slug: "money_stewardship",
    name_ko: "돈과 청지기",
    pack_binding: "wealth",
    re: /재물|탐심|돈\s*사랑|돈을\s*사랑|부에\s*대해|wealth|mammon|십일조|헌금/i,
    weight: 80,
  },
  {
    id_slug: "speech_truth",
    name_ko: "말과 진실",
    pack_binding: "speech",
    re: /정직|거짓\s*말|거짓\s*서류|거짓\s*증|서명하(?:라|라고)|말조심|혀를\s*삼|말에\s*관한|말이\s*화|혀의\s*죄|말의\s*힘|truthful\s*speech/i,
    weight: 80,
  },
  {
    id_slug: "relationships_reconciliation",
    name_ko: "관계와 화해",
    pack_binding: "love_enemy",
    re: /관계\s*회복|화해|원수를\s*사랑|미워하는\s*사람.{0,12}사랑|love\s*(?:your\s*)?enem|reconcile/i,
    weight: 85,
  },
  {
    id_slug: "family_marriage",
    name_ko: "가정과 결혼",
    pack_binding: "family",
    re: /부모\s*공경|부모님을\s*공경|결혼|부부|자녀\s*양육|honor\s*(?:your\s*)?father/i,
    weight: 78,
  },
  {
    id_slug: "psalms_devotional",
    name_ko: "시편 묵상",
    pack_binding: "psalm23",
    re: /시편(?:으로|으로\s*기도|묵상)|시편\s*23|시\s*23|psalm\s*23|목자/i,
    weight: 92,
  },
  {
    id_slug: "suffering_trials",
    name_ko: "고난과 시험",
    pack_binding: "patience",
    re: /인내(?:에|란|는|를|하)|patience|endure/i,
    weight: 79,
  },
  {
    id_slug: "suffering_trials",
    name_ko: "고난과 시험",
    pack_binding: "job",
    re: /욥기|욥이?\s*고난|욥의\s*고난|고난을\s*받|job\s*(?:suffer|book)|왜\s*고난|고난을\s*받은\s*이유/i,
    weight: 80,
  },
  {
    id_slug: "salvation_faith",
    name_ko: "구원과 믿음",
    pack_binding: "faith_core",
    re: /신앙(?:이란|은|이\s*무엇)|믿음(?:이란|은|이\s*무엇|으로)|은혜로\s*구원|what\s+is\s+faith|칭의(?:란|는)|구원(?:이란|은\s*무엇)/i,
    weight: 75,
  },
  {
    id_slug: "gospel_core",
    name_ko: "복음 핵심",
    pack_binding: "faith_core",
    re: /복음(?:이\s*뭐|이란|은\s*무엇|의\s*내용)|복음\s*전하는\s*구절|gospel\s*(?:is|mean)/i,
    weight: 74,
  },
  {
    id_slug: "jesus_person_work",
    name_ko: "예수님의 인격과 사역",
    pack_binding: "cross",
    re: /십자가.{0,8}(?:의미|뜻)|cross.{0,12}mean|예수님.?이?\s*왜\s*오|예수님은\s*왜\s*오셨|예수님의\s*중보|부활의\s*의미|jesus.{0,12}(?:come|intercess)/i,
    weight: 80,
  },
  {
    id_slug: "angels_demons",
    name_ko: "천사와 악한 영",
    pack_binding: "angels",
    re: /천사|귀신|타락한\s*천사|사탄의\s*선택|angel|demon|free\s*will.{0,12}(?:angel|사탄)/i,
    weight: 78,
  },
  {
    id_slug: "law_commands",
    name_ko: "율법과 계명",
    pack_binding: "decalogue",
    re: /십계명|계명|탐내지\s*말|도둑질|간음|살인\s*하지|우상|안식일|거짓\s*증거|일요일.{0,8}교회/i,
    weight: 77,
  },
  {
    id_slug: "creation_origins",
    name_ko: "창조와 기원",
    pack_binding: "creation",
    re: /창조|7\s*일|칠일|진화론|유신진화|유인원|공룡|우주.{0,12}(?:년|억)|과학은\s*진실|흙으로\s*만드|아담은/i,
    weight: 86,
  },
  {
    id_slug: "holy_spirit",
    name_ko: "성령",
    pack_binding: "holy_spirit",
    re: /성령\s*충만|성령의\s*열매|성령(?:이란|은|이\s*무엇)|방언|성령을?\s*못\s*받|holy\s*spirit|tongues?/i,
    weight: 80,
  },
  {
    id_slug: "church_fellowship",
    name_ko: "교회와 교제",
    pack_binding: "church",
    re: /교회(?:란|는|가\s*왜|의\s*의미)|성도의\s*교제|church\s*(?:is|mean|why)/i,
    weight: 78,
  },
  {
    id_slug: "worship_thanksgiving",
    name_ko: "예배와 감사",
    pack_binding: "thanksgiving",
    re: /감사하는\s*마음|감사\s*구절|예배(?:의\s*뜻|란)|thanksgiving|worship/i,
    weight: 76,
  },
  {
    id_slug: "prophecy_hope_watchfulness",
    name_ko: "종말 소망·깨어있음",
    pack_binding: "prophecy_hope",
    re: /재림을\s*기다리|종말\s*소망|깨어\s*있으라|마태\s*24|watchfulness|second\s*coming/i,
    weight: 70,
  },
  {
    id_slug: "god_character",
    name_ko: "하나님 성품",
    pack_binding: "god_character",
    re: /하나님은\s*어떤\s*분|하나님의\s*신실|하나님의\s*사랑(?:이란|은)|god'?s?\s*character/i,
    weight: 72,
  },
  {
    id_slug: "spiritual_growth",
    name_ko: "영적 성장",
    pack_binding: "growth",
    re: /영적\s*성숙|믿음이\s*자라|제자도|spiritual\s*growth/i,
    weight: 70,
  },
  {
    id_slug: "healing_sickness",
    name_ko: "질병과 치유",
    pack_binding: "healing",
    re: /아플\s*때|몸이\s*아플|치유를\s*위한|병중\s*위로|치유|healing\s*(?:verse|prayer)/i,
    weight: 72,
  },
  {
    id_slug: "death_eternal_hope",
    name_ko: "죽음과 영원 소망",
    pack_binding: "death_hope",
    re: /죽음이?\s*두려워|죽음.{0,12}두려움|죽음에\s*대한|영생\s*소망|영생\s*구절|부활\s*소망|eternal\s*life/i,
    weight: 72,
  },
  {
    id_slug: "wisdom_guidance",
    name_ko: "지혜와 인도",
    pack_binding: "wisdom",
    re: /결정\s*앞에서\s*지혜|하나님의\s*뜻을\s*알고|지혜를\s*구|guidance\s*verse/i,
    weight: 70,
  },
  {
    id_slug: "work_vocation",
    name_ko: "일과 직업",
    pack_binding: "work",
    re: /직장에서\s*지칠|일의\s*의미|직업과\s*신앙|vocation|work\s*(?:ethic|meaning)/i,
    weight: 70,
  },
  {
    id_slug: "mission_evangelism",
    name_ko: "선교와 전도",
    pack_binding: "mission",
    re: /복음.{0,8}전하|전도\s*관련|선교의\s*이유|복음\s*전하는|evangelism|great\s*commission|부모님.{0,40}(?:불교|타종교)|(?:불교|타종교).{0,40}크리스천|크리스천이\s*된\s*걸/i,
    weight: 70,
  },
  {
    id_slug: "service_calling",
    name_ko: "섬김과 부르심",
    pack_binding: "service",
    re: /섬김의\s*자세|하나님이\s*주신\s*일|소명|calling\s*to\s*serve/i,
    weight: 68,
  },
  {
    id_slug: "justice_mercy",
    name_ko: "정의와 자비",
    pack_binding: "justice",
    re: /정의와\s*자비|이웃\s*돌봄|가난한\s*자\s*돌봄|약자\s*보호|justice\s*(?:and\s*)?mercy/i,
    weight: 68,
  },
  {
    id_slug: "sexuality_purity",
    name_ko: "성과 순결",
    pack_binding: "purity",
    re: /순결에\s*대한|성적\s*유혹|음행|sexual\s*purity|문신|타투|혼전|tattoo|sex\s*before\s*marriage|성경은\s*동성애/i,
    weight: 75,
  },
  {
    id_slug: "scripture_word",
    name_ko: "말씀과 묵상",
    pack_binding: "scripture",
    re: /성경\s*읽는\s*습관|성경.{0,12}읽|레위기.{0,16}막히|어디부터\s*(?:다시\s*)?읽|말씀의\s*능력|묵상\s*방법|meditat|성경에?\s*모순|성경\s*신뢰|bible\s*contradictions?|정경/i,
    weight: 65,
  },
  {
    id_slug: "obedience_holiness",
    name_ko: "순종과 거룩",
    pack_binding: "obedience",
    re: /거룩하게\s*산다|순종\s*관련|holiness|obedience\s*verse/i,
    weight: 65,
  },
  {
    id_slug: "forgiveness_grace",
    name_ko: "용서와 은혜",
    pack_binding: "forgiveness",
    re: /용서하기|남을\s*용서|하나님이\s*용서|은혜로?\s*회복|은혜의\s*회복|forgiv(?:e|eness)/i,
    weight: 72,
  },
  {
    id_slug: "temptation_spiritual_warfare",
    name_ko: "유혹과 영적 전쟁",
    pack_binding: "temptation",
    // Alcohol/절주 cues moved to temperance_abstinence (dedicated L2 · not soft-absorb).
    re: /유혹|영적\s*전쟁|마귀\s*대적|spiritual\s*warfare|temptation/i,
    weight: 74,
  },
  {
    id_slug: "temperance_abstinence",
    name_ko: "절주·절제(음주)",
    pack_binding: "temperance",
    re: /술자리|술을?\s*(?:끊|마시)|한두\s*잔|절주|술을\s*아예\s*끊|음주\s*절제|금주|취하지\s*말|술\s*끊|wine\s*(?:and\s*)?temperance|abstain(?:ence)?\s*from\s*(?:alcohol|wine)|christian.{0,20}drink/i,
    weight: 78,
  },
];

const CONFLICT_RULES: Array<{
  id: string;
  apply: (q: string, hits: DrawerRoute[]) => DrawerRoute | null;
}> = [
  {
    id: "healing_vs_comfort_sickness",
    apply: (q, hits) => {
      if (!/아플|병중|치유|healing|sickness/i.test(q)) return null;
      return hits.find((h) => h.id_slug === "healing_sickness") ?? null;
    },
  },
  {
    id: "jesus_intercession_vs_prayer",
    apply: (q, hits) => {
      if (!/예수|그리스도|jesus|christ/i.test(q)) return null;
      if (!/중보|간구하심|intercess/i.test(q)) return null;
      return hits.find((h) => h.id_slug === "jesus_person_work") ?? null;
    },
  },
  {
    id: "gospel_vs_mission_phrase",
    apply: (q, hits) => {
      if (/복음\s*전하는\s*구절|복음(?:이\s*뭐|이란|은\s*무엇|의\s*내용)/i.test(q)) {
        return hits.find((h) => h.id_slug === "gospel_core") ?? null;
      }
      return null;
    },
  },
  {
    id: "guilt_to_sin_repentance",
    apply: (q, hits) => {
      if (!/죄책|양심|회개|돌이키|guilt|repent/i.test(q)) return null;
      const sin = hits.find((h) => h.id_slug === "sin_repentance");
      return sin ?? null;
    },
  },
  {
    id: "comfort_vs_fear_vs_assurance",
    apply: (q, hits) => {
      const hasComfort = hits.some((h) => h.id_slug === "comfort_lament");
      const hasFear = hits.some((h) => h.id_slug === "fear_anxiety");
      const hasAssur = hits.some((h) => h.id_slug === "assurance_peace");
      if (/구원\s*확신|정죄/i.test(q) && hasAssur) {
        return hits.find((h) => h.id_slug === "assurance_peace") ?? null;
      }
      if (/슬픔|애통|애도|상실|위로가\s*되는|악몽|읽어주면/i.test(q) && hasComfort) {
        return hits.find((h) => h.id_slug === "comfort_lament") ?? null;
      }
      if (
        (/힘들\s*때|곁에|두려워|불안|염려|걱정|임재|담대/i.test(q) && hasFear) ||
        (hasFear && !hasComfort)
      ) {
        return hits.find((h) => h.id_slug === "fear_anxiety") ?? null;
      }
      return null;
    },
  },
  {
    id: "marriage_over_bare_assurance",
    apply: (q, hits) => {
      if (!/결혼|부부|약혼/i.test(q)) return null;
      // Salvation-assurance still wins when explicit.
      if (/구원\s*확신|정죄|영생/i.test(q)) return null;
      return hits.find((h) => h.id_slug === "family_marriage") ?? null;
    },
  },
  {
    id: "funeral_to_death_hope",
    apply: (q, hits) => {
      if (!/장례|죽음이?\s*두려워|영생\s*소망/i.test(q)) return null;
      // Hell/condemnation fear at deathbed → assurance, not death_hope softpack theater.
      if (/지옥/i.test(q)) {
        return hits.find((h) => h.id_slug === "assurance_peace") ?? null;
      }
      return hits.find((h) => h.id_slug === "death_eternal_hope") ?? null;
    },
  },
  {
    id: "hell_fear_to_assurance",
    apply: (q, hits) => {
      if (!/지옥/i.test(q)) return null;
      if (!/무섭|두려|죽을\s*때|정죄|구원/i.test(q)) return null;
      return hits.find((h) => h.id_slug === "assurance_peace") ?? null;
    },
  },
  {
    id: "parents_other_religion_to_mission",
    apply: (q, hits) => {
      if (!/부모/i.test(q)) return null;
      if (!/(?:불교|타종교|힌두|이슬람|무교)/i.test(q)) return null;
      if (!/(?:크리스천|그리스도인|예수|신앙|믿음)/i.test(q)) return null;
      return hits.find((h) => h.id_slug === "mission_evangelism") ?? null;
    },
  },
  {
    id: "alcohol_to_temperance",
    apply: (q, hits) => {
      if (
        !/술자리|술을?\s*(?:끊|마시)|한두\s*잔|절주|술을\s*아예\s*끊|음주\s*절제|금주|취하지\s*말|wine|alcohol|temperance|abstinen/i.test(
          q,
        )
      ) {
        return null;
      }
      return hits.find((h) => h.id_slug === "temperance_abstinence") ?? null;
    },
  },
  {
    id: "psalm23_ref_explicit",
    apply: (q, hits) => {
      if (!/시편\s*23|시\s*23|psalm\s*23/i.test(q)) return null;
      return hits.find((h) => h.id_slug === "psalms_devotional") ?? null;
    },
  },
];

export function resolveAskDrawerV1(query: string): AskDrawerResolveV1 {
  const qRaw = String(query || "").trim();
  const q = normalizeAskQueryKoV1(qRaw) || qRaw;
  if (!qRaw) {
    return {
      drawer_id: "unmapped_hold",
      name_ko: "미분류 보류",
      matched: false,
      pack_binding: null,
      reason_ko: "empty",
      conflict_rule_id: null,
    };
  }

  // Primary RE on raw + normalized (spacing/punct only).
  const hits = DRAWER_ROUTES.filter((r) => r.re.test(qRaw) || r.re.test(q));
  if (hits.length === 0) {
    // Lemma synonym layer — systematic colloquial cues (≠ per-sentence RE patch).
    const lemma = pickUniqueLemmaDrawerV1(qRaw);
    if (lemma) {
      return {
        drawer_id: lemma.id_slug,
        name_ko: lemma.name_ko,
        matched: true,
        pack_binding: lemma.pack_binding,
        reason_ko: `lemma:${lemma.hits}`,
        conflict_rule_id: null,
      };
    }
    return {
      drawer_id: "unmapped_hold",
      name_ko: "미분류 보류",
      matched: false,
      pack_binding: null,
      reason_ko: "no_drawer_cue",
      conflict_rule_id: null,
    };
  }

  let conflictId: string | null = null;
  let chosen: DrawerRoute | null = null;
  for (const rule of CONFLICT_RULES) {
    const c = rule.apply(q, hits);
    if (c) {
      chosen = c;
      conflictId = rule.id;
      break;
    }
  }

  if (!chosen) {
    const sorted = [...hits].sort((a, b) => b.weight - a.weight);
    const top = sorted[0];
    const tied = sorted.filter((h) => h.weight === top.weight && h.id_slug !== top.id_slug);
    // Same drawer different bindings (prayer vs intercession) OK — pick higher weight already unique.
    // Different drawers same weight → unmapped (no forced nearest).
    if (tied.length > 0 && tied.some((t) => t.id_slug !== top.id_slug)) {
      const otherDrawers = new Set(tied.map((t) => t.id_slug).filter((id) => id !== top.id_slug));
      if (otherDrawers.size > 0) {
        return {
          drawer_id: "unmapped_hold",
          name_ko: "미분류 보류",
          matched: false,
          pack_binding: null,
          reason_ko: `tie_weight_${top.weight}`,
          conflict_rule_id: null,
        };
      }
    }
    chosen = top;
  }

  return {
    drawer_id: chosen.id_slug,
    name_ko: chosen.name_ko,
    matched: true,
    pack_binding: chosen.pack_binding,
    reason_ko: conflictId ? `conflict:${conflictId}` : `weight:${chosen.weight}`,
    conflict_rule_id: conflictId,
  };
}

/** True when taxonomy knows the drawer but Level-2 pack is not wired yet. */
export function isDrawerKnownWithoutPack(res: AskDrawerResolveV1): boolean {
  return res.matched && res.pack_binding === null && res.drawer_id !== "unmapped_hold";
}
