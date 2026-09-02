/**
 * Drawer query normalize + lemma synonym layer (batch5 hold diagnosis).
 *
 * Systematic cues — NOT per-prompt RE patches for batch5 sentences.
 * research_only · [NON_GATING] · send_gate HOLD
 */
import type { AskDrawerPackBinding } from "./logosAskDrawerRouterV1";

export type DrawerLemmaGroupV1 = {
  id_slug: string;
  name_ko: string;
  pack_binding: AskDrawerPackBinding;
  weight: number;
  /** Any matching lemma contributes 1 hit. */
  lemmas: RegExp[];
  min_hits: number;
};

/** Light normalize for cue matching (does not rewrite user-facing text). */
export function normalizeAskQueryKoV1(query: string): string {
  return String(query || "")
    .normalize("NFKC")
    .replace(/[\u200b\uFEFF]/g, "")
    .replace(/하느님/g, "하나님")
    .replace(/[？?！!.,，。…~～]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Synonym / colloquial lemma groups — drawer-level, not sentence-level.
 * Tuned for natural speech gaps (hold/no_drawer_cue class).
 */
export const DRAWER_LEMMA_GROUPS_V1: DrawerLemmaGroupV1[] = [
  {
    id_slug: "assurance_peace",
    name_ko: "확신과 평안",
    pack_binding: "assurance",
    weight: 74,
    min_hits: 1,
    lemmas: [
      /괜찮은\s*사람/,
      /진짜로\s*괜찮은/,
      /구원.?확신/,
      /정죄(?:감|가|없)?/,
      /(?:구원|영생|정죄).{0,12}확신이\s*없/,
      /내가\s*괜찮은지/,
      /지옥.{0,20}무섭/,
      /지옥이?\s*두려/,
      /죽을\s*때.{0,24}지옥/,
    ],
  },
  {
    id_slug: "forgiveness_grace",
    name_ko: "용서와 은혜",
    pack_binding: "forgiveness",
    weight: 73,
    min_hits: 1,
    lemmas: [/놓아주/, /풀어주/, /분이\s*치밀/, /용서하기|남을\s*용서/, /은혜로?\s*회복/],
  },
  {
    id_slug: "temptation_spiritual_warfare",
    name_ko: "유혹과 영적 전쟁",
    pack_binding: "temptation",
    weight: 73,
    min_hits: 1,
    lemmas: [/그\s*버릇|나쁜\s*버릇|또\s*그\s*버릇/, /버티고\s*싶/, /유혹/, /손짓하는데/],
  },
  {
    id_slug: "prophecy_hope_watchfulness",
    name_ko: "종말 소망·깨어있음",
    pack_binding: "prophecy_hope",
    weight: 68,
    min_hits: 1,
    lemmas: [
      /기다림에\s*지쳐/,
      /언제\s*끝날지\s*모르는\s*기다림/,
      /재림|깨어\s*있으/,
      /종말\s*소망/,
    ],
  },
  {
    id_slug: "god_character",
    name_ko: "하나님 성품",
    pack_binding: "god_character",
    weight: 72,
    min_hits: 1,
    lemmas: [
      /어떤\s*성품|원래\s*어떤\s*성품/,
      /하나님은\s*어떤\s*분/,
      /버리신\s*건\s*아닌지/,
      /하나님의\s*신실/,
    ],
  },
  {
    id_slug: "wisdom_guidance",
    name_ko: "지혜와 인도",
    pack_binding: "wisdom",
    weight: 70,
    min_hits: 1,
    lemmas: [/이직할지|이직\s*말지/, /머릿속이\s*하얘/, /갈피를\s*못/, /지혜를\s*구/, /결정을\s*앞/],
  },
  {
    id_slug: "healing_sickness",
    name_ko: "질병과 치유",
    pack_binding: "healing",
    weight: 74,
    min_hits: 1,
    lemmas: [/병원\s*다니/, /아플\s*때|몸이\s*아플/, /병중|치유/, /마음만은\s*붙잡/],
  },
  {
    id_slug: "death_eternal_hope",
    name_ko: "죽음과 영원 소망",
    pack_binding: "death_hope",
    weight: 76,
    min_hits: 1,
    lemmas: [/장례식|장례\s*다녀/, /죽음이?\s*두려워|죽음에\s*대한/, /영생\s*소망/, /밤이\s*무서워/],
  },
  {
    id_slug: "mission_evangelism",
    name_ko: "선교와 전도",
    pack_binding: "mission",
    weight: 72,
    min_hits: 1,
    lemmas: [/믿음\s*얘기/, /복음.{0,8}전하/, /전도|선교/, /입이\s*안\s*떨어져/],
  },
  {
    id_slug: "jesus_person_work",
    name_ko: "예수님의 인격과 사역",
    pack_binding: "cross",
    weight: 74,
    min_hits: 1,
    lemmas: [
      /우리\s*편이라는/,
      /예수님.?이?\s*왜\s*오/,
      /그분이\s*우리\s*편/,
      /십자가.{0,8}(?:의미|뜻)/,
    ],
  },
  // Batch7 cover queue — drawer-level systematic cues (≠ per-sentence RE theater).
  {
    id_slug: "comfort_lament",
    name_ko: "위로와 탄식",
    pack_binding: "comfort_sorrow",
    weight: 75,
    min_hits: 1,
    lemmas: [
      /악몽/,
      /아이에게\s*읽어/,
      /읽어주면\s*좋은\s*말씀/,
      /아이.{0,12}악몽/,
      /가족을?\s*잃/,
      /원망스러/,
      /하나님.{0,12}원망/,
      /사별|별세|애도|탄식/,
    ],
  },
  {
    id_slug: "speech_truth",
    name_ko: "말과 진실",
    pack_binding: "speech",
    weight: 75,
    min_hits: 1,
    lemmas: [/거짓\s*서류/, /서명하(?:라|라고)/, /거짓\s*증/, /상사.{0,16}서명/],
  },
  {
    id_slug: "money_stewardship",
    name_ko: "돈과 청지기",
    pack_binding: "wealth",
    weight: 75,
    min_hits: 1,
    lemmas: [/십일조/, /드릴\s*게\s*없어서/, /헌금/],
  },
  {
    id_slug: "holy_spirit",
    name_ko: "성령",
    pack_binding: "holy_spirit",
    weight: 75,
    min_hits: 1,
    lemmas: [/방언/, /성령을?\s*못\s*받/],
  },
  {
    id_slug: "temperance_abstinence",
    name_ko: "절주·절제(음주)",
    pack_binding: "temperance",
    weight: 78,
    min_hits: 1,
    lemmas: [/술자리/, /한두\s*잔/, /술을\s*아예\s*끊/, /절주/, /금주/, /음주\s*절제/],
  },
  {
    id_slug: "mission_evangelism",
    name_ko: "선교와 전도",
    pack_binding: "mission",
    weight: 76,
    min_hits: 1,
    lemmas: [
      /부모님.{0,40}불교/,
      /불교.{0,40}크리스천/,
      /크리스천이\s*된\s*걸/,
      /타종교.{0,16}부모/,
    ],
  },
  {
    id_slug: "scripture_word",
    name_ko: "말씀과 묵상",
    pack_binding: "scripture",
    weight: 74,
    min_hits: 1,
    lemmas: [/레위기.{0,16}막히/, /어디부터\s*(?:다시\s*)?읽/, /성경.{0,12}읽/],
  },
];

export type LemmaHitV1 = {
  id_slug: string;
  name_ko: string;
  pack_binding: AskDrawerPackBinding;
  weight: number;
  hits: number;
};

export function scoreDrawerLemmaHitsV1(query: string): LemmaHitV1[] {
  const q = normalizeAskQueryKoV1(query);
  if (!q) return [];
  const out: LemmaHitV1[] = [];
  for (const g of DRAWER_LEMMA_GROUPS_V1) {
    let hits = 0;
    for (const re of g.lemmas) {
      if (re.test(q)) hits += 1;
    }
    if (hits >= g.min_hits) {
      out.push({
        id_slug: g.id_slug,
        name_ko: g.name_ko,
        pack_binding: g.pack_binding,
        weight: g.weight + Math.min(hits, 3),
        hits,
      });
    }
  }
  return out.sort((a, b) => b.weight - a.weight || b.hits - a.hits);
}

/** Unique top lemma drawer or null (tie → null = keep unmapped). */
export function pickUniqueLemmaDrawerV1(query: string): LemmaHitV1 | null {
  const scored = scoreDrawerLemmaHitsV1(query);
  if (scored.length === 0) return null;
  const top = scored[0];
  const tied = scored.filter(
    (s) => s.weight === top.weight && s.id_slug !== top.id_slug,
  );
  if (tied.length > 0) return null;
  return top;
}
