/**
 * Drawer Level-2 soft packs — remaining taxonomy drawers (commander 「순서대로해」).
 * seed families from HQ consult [HYPO] · research_only · soft citation · no Destiny.
 */
import type { AskDrawerResolveV1 } from "./logosAskDrawerRouterV1";

export const FREEFORM_TOPICAL_PRESET_ID = "dynamic_topical_freeform";
export const FREEFORM_WEAK_CITATION_BANNER_KO =
  "근거 연결이 약합니다 · 연구 참고";

export type DrawerL2PackDef = {
  binding: string;
  drawer_id: string;
  query_mode: string;
  refs: readonly string[];
  one_liner_ko: string;
  title_ko: string;
  bullets_ko: string[];
};

/** Remaining drawers in taxonomy / router order. */
export const DRAWER_L2_REMAINING_PACKS: DrawerL2PackDef[] = [
  {
    binding: "assurance",
    drawer_id: "assurance_peace",
    query_mode: "inquiry_thematic_assurance_peace",
    refs: ["1John.5.13", "Rom.8.1", "John.14.27", "Phil.4.7"],
    one_liner_ko: "assurance — 1John.5.13 · Rom.8.1 · John.14.27 [HYPO]",
    title_ko: "확신과 평안",
    bullets_ko: [
      "- **요한일서 5.13 / 로마 8.1:** 영생 확신 · 정죄 없음.",
      "- **요한 14.27 / 빌립보 4.7:** 평안을 너희에게 끼치노니.",
    ],
  },
  {
    binding: "forgiveness",
    drawer_id: "forgiveness_grace",
    query_mode: "inquiry_thematic_forgiveness_grace",
    refs: ["Matt.6.14", "Eph.4.32", "Col.3.13", "Ps.130.4"],
    one_liner_ko: "forgiveness — Matt.6.14 · Eph.4.32 · Col.3.13 [HYPO]",
    title_ko: "용서와 은혜",
    bullets_ko: [
      "- **마태 6.14 / 에베소 4.32:** 용서하면 너희도 사함을 받고 · 서로 용서하라.",
      "- **시편 130.4:** 사유하심이 주께 있음은.",
    ],
  },
  {
    binding: "scripture",
    drawer_id: "scripture_word",
    query_mode: "inquiry_thematic_scripture_word",
    refs: ["Ps.1.2", "Ps.119.105", "2Tim.3.16", "Heb.4.12"],
    one_liner_ko: "scripture — Ps.119.105 · 2Tim.3.16 · Heb.4.12 [HYPO]",
    title_ko: "말씀과 묵상",
    bullets_ko: [
      "- **시편 119.105 / 디모데후서 3.16:** 등불이요 · 모든 성경은 하나님의 감동.",
      "- **히브리서 4.12:** 말씀은 살았고 운동력이 있어.",
      "- **모순·정경·신뢰 FAQ:** 학파 병렬만 · 외부 FAQ 본문 복제·역본 재판 금지 (Wave6 densify).",
    ],
  },
  {
    binding: "obedience",
    drawer_id: "obedience_holiness",
    query_mode: "inquiry_thematic_obedience_holiness",
    refs: ["1Pet.1.15", "Rom.12.1", "John.14.15", "Heb.12.14"],
    one_liner_ko: "obedience — 1Pet.1.15 · Rom.12.1 · John.14.15 [HYPO]",
    title_ko: "순종과 거룩",
    bullets_ko: [
      "- **베드로전서 1.15 / 요한 14.15:** 거룩하라 · 나를 사랑하면 계명을 지키라.",
      "- **로마 12.1:** 산 제사로 드리라.",
    ],
  },
  {
    binding: "growth",
    drawer_id: "spiritual_growth",
    query_mode: "inquiry_thematic_spiritual_growth",
    refs: ["Col.2.6", "2Pet.3.18", "Heb.5.14", "John.15.5"],
    one_liner_ko: "growth — Col.2.6 · 2Pet.3.18 · John.15.5 [HYPO]",
    title_ko: "영적 성장",
    bullets_ko: [
      "- **골로새 2.6 / 베드로후서 3.18:** 그 안에서 행하라 · 은혜와 지식에 자라 가라.",
      "- **요한 15.5:** 가지가 포도나무에 붙어 있지 않으면.",
    ],
  },
  {
    binding: "temptation",
    drawer_id: "temptation_spiritual_warfare",
    query_mode: "inquiry_thematic_temptation_spiritual_warfare",
    refs: ["Matt.4.1", "1Cor.10.13", "Eph.6.11", "Jas.4.7"],
    one_liner_ko: "temptation — 1Cor.10.13 · Eph.6.11 · Jas.4.7 [HYPO]",
    title_ko: "유혹과 영적 전쟁",
    bullets_ko: [
      "- **고린도전서 10.13:** 감당치 못할 시험 없으며.",
      "- **에베소 6.11 / 야고보 4.7:** 마귀의 궤계를 능히 대적 · 마귀를 대적하라.",
      "- 절주·음주 질문은 temperance_abstinence 전용 팩으로 보냄(이 팩에 soft-absorb 금지).",
    ],
  },
  {
    binding: "temperance",
    drawer_id: "temperance_abstinence",
    query_mode: "inquiry_thematic_temperance_abstinence",
    refs: ["Prov.20.1", "Eph.5.18", "Prov.23.31", "Rom.14.21", "1Cor.6.12"],
    one_liner_ko: "temperance — Prov.20.1 · Eph.5.18 · Rom.14.21 [HYPO]",
    title_ko: "절주·절제(음주)",
    bullets_ko: [
      "- **잠언 20.1 / 에베소 5.18:** 포도주는 거만하게 하는 것 · 술 취하지 말라.",
      "- **잠언 23.31 / 로마 14.21:** 포도주를 보지 말 것이며 · 고기를 먹지 아니하며 포도주를 마시지 아니하는 것이 좋으니.",
      "- **고린도전서 6.12:** 모든 것이 가하나 내게 제압되지 아니하리라 — 절제 축(연구).",
      "- 의료·재활·금단 처방 아님 · cover 밖(병원 추천·임상 중독 프로토콜)은 offtopic/HOLD.",
    ],
  },
  {
    binding: "healing",
    drawer_id: "healing_sickness",
    query_mode: "inquiry_thematic_healing_sickness",
    refs: ["Ps.103.3", "Jas.5.14", "Jas.5.15", "Mark.5.34"],
    one_liner_ko: "healing — Ps.103.3 · Jas.5.14 · Mark.5.34 [HYPO]",
    title_ko: "질병과 치유",
    bullets_ko: [
      "- **시편 103.3 / 야고보 5.14–15:** 모든 병을 고치시며 · 기름을 바르며 기도하라.",
      "- 의료 대체·진단 아님 · 연구 참고만.",
    ],
  },
  {
    binding: "death_hope",
    drawer_id: "death_eternal_hope",
    query_mode: "inquiry_thematic_death_eternal_hope",
    refs: ["John.11.25", "1Cor.15.54", "1Thess.4.14", "Rev.21.4"],
    one_liner_ko: "death_hope — John.11.25 · 1Cor.15.54 · Rev.21.4 [HYPO]",
    title_ko: "죽음과 영원 소망",
    bullets_ko: [
      "- **요한 11.25 / 고린도전서 15.54:** 부활이요 생명이니 · 사망이 이김의 삼킨 바 되리라.",
      "- 날짜·시대표 계산 금지.",
    ],
  },
  {
    binding: "service",
    drawer_id: "service_calling",
    query_mode: "inquiry_thematic_service_calling",
    refs: ["Rom.12.6", "1Pet.4.10", "Mic.6.8", "Col.3.23"],
    one_liner_ko: "service — Rom.12.6 · 1Pet.4.10 · Mic.6.8 [HYPO]",
    title_ko: "섬김과 부르심",
    bullets_ko: [
      "- **로마 12.6 / 베드로전서 4.10:** 은사대로 · 서로 봉사하라.",
      "- 직업 점치기·미래 계시 아님.",
    ],
  },
  {
    binding: "mission",
    drawer_id: "mission_evangelism",
    query_mode: "inquiry_thematic_mission_evangelism",
    refs: ["Matt.28.19", "Acts.1.8", "Rom.10.14", "1Pet.3.15"],
    one_liner_ko: "mission — Matt.28.19 · Acts.1.8 · 1Pet.3.15 [HYPO]",
    title_ko: "선교와 전도",
    bullets_ko: [
      "- **마태 28.19 / 사도행전 1.8:** 제자를 삼아 · 땅 끝까지 증인.",
      "- 문화전쟁 담론 아님.",
    ],
  },
  {
    binding: "wisdom",
    drawer_id: "wisdom_guidance",
    query_mode: "inquiry_thematic_wisdom_guidance",
    refs: ["Prov.3.5", "Prov.3.6", "Jas.1.5", "Ps.32.8"],
    one_liner_ko: "wisdom — Prov.3.5 · Jas.1.5 · Ps.32.8 [HYPO]",
    title_ko: "지혜와 인도",
    bullets_ko: [
      "- **잠언 3.5–6 / 야고보 1.5:** 여호와를 신뢰하라 · 지혜를 구하라.",
      "- 개인 미래 점치기 금지.",
    ],
  },
  {
    binding: "work",
    drawer_id: "work_vocation",
    query_mode: "inquiry_thematic_work_vocation",
    refs: ["Gen.2.15", "Col.3.23", "Prov.16.3", "2Thess.3.10"],
    one_liner_ko: "work — Gen.2.15 · Col.3.23 · Prov.16.3 [HYPO]",
    title_ko: "일과 직업",
    bullets_ko: [
      "- **창세기 2.15 / 골로새 3.23:** 경작하며 지키게 · 주께 하듯 하고.",
      "- 투자·수익률 전략 아님.",
    ],
  },
  {
    binding: "justice",
    drawer_id: "justice_mercy",
    query_mode: "inquiry_thematic_justice_mercy",
    refs: ["Mic.6.8", "Isa.58.6", "Amos.5.24", "Luke.4.18"],
    one_liner_ko: "justice — Mic.6.8 · Amos.5.24 · Luke.4.18 [HYPO]",
    title_ko: "정의와 자비",
    bullets_ko: [
      "- **미가 6.8 / 아모스 5.24:** 공의와 인자를 사랑하며 · 정의가 물같이.",
      "- 정당·정책 처방 아님.",
    ],
  },
  {
    binding: "purity",
    drawer_id: "sexuality_purity",
    query_mode: "inquiry_thematic_sexuality_purity",
    refs: ["1Cor.6.18", "1Thess.4.3", "Matt.5.28", "Ps.119.9"],
    one_liner_ko: "purity — 1Cor.6.18 · 1Thess.4.3 · Matt.5.28 [HYPO]",
    title_ko: "성과 순결",
    bullets_ko: [
      "- **고린도전서 6.18 / 데살로니가전서 4.3:** 음행을 피하라 · 거룩함.",
      "- 성윤리 전면 판결 아님 · 연구 참고.",
      "- **문신·혼전 FAQ:** 학파 병렬만 · 법률·강제 교정 Final Action 금지 (Wave6 densify).",
    ],
  },
  {
    binding: "god_character",
    drawer_id: "god_character",
    query_mode: "inquiry_thematic_god_character",
    refs: ["Exod.34.6", "Ps.103.8", "Mal.3.6", "1John.4.8"],
    one_liner_ko: "god_character — Exod.34.6 · Ps.103.8 · 1John.4.8 [HYPO]",
    title_ko: "하나님 성품",
    bullets_ko: [
      "- **출애굽 34.6 / 시편 103.8:** 자비롭고 은혜롭고 · 노하기를 더디 하시며.",
      "- 삼위일체 세부 논쟁 전부 흡수 금지.",
    ],
  },
  {
    binding: "prophecy_hope",
    drawer_id: "prophecy_hope_watchfulness",
    query_mode: "inquiry_thematic_prophecy_hope_watchfulness",
    refs: ["Matt.24.42", "1Thess.5.6", "2Pet.3.12", "Rev.22.20"],
    one_liner_ko: "prophecy_hope — Matt.24.42 · 1Thess.5.6 · Rev.22.20 [HYPO]",
    title_ko: "종말 소망·깨어있음",
    bullets_ko: [
      "- **마태 24.42 / 데살로니가전서 5.6:** 깨어 있으라 · 다른 이들과 같이 자지 말고.",
      "- 날짜·시대표·매매 신호 금지.",
    ],
  },
];

/** Gap soft packs — taxonomy example coverage (commander 「완성도를 올려봐」). */
export const DRAWER_L2_GAP_PACKS: DrawerL2PackDef[] = [
  {
    binding: "cross",
    drawer_id: "jesus_person_work",
    query_mode: "inquiry_thematic_jesus_person_work",
    refs: ["John.1.14", "John.3.16", "Rom.5.8", "Heb.7.25"],
    one_liner_ko: "jesus — John.3.16 · Rom.5.8 · Heb.7.25 [HYPO]",
    title_ko: "예수님의 인격과 사역",
    bullets_ko: [
      "- **요한 3.16 / 로마 5.8:** 독생자를 주셨으니 · 우리를 위하여 죽으심.",
      "- **히브리서 7.25:** 항상 살아서 간구하심(중보 축).",
      "- 종말 타임라인·날짜 계산 금지.",
    ],
  },
  {
    binding: "faith_core",
    drawer_id: "salvation_faith",
    query_mode: "inquiry_thematic_salvation_faith",
    refs: ["Eph.2.8", "Rom.3.24", "John.3.16", "Rom.10.9"],
    one_liner_ko: "salvation_faith — Eph.2.8 · Rom.3.24 · John.3.16 [HYPO]",
    title_ko: "구원과 믿음",
    bullets_ko: [
      "- **에베소 2.8 / 로마 3.24:** 은혜로 구원 · 그리스도 예수 안에 있는 속량.",
      "- 회개 실천·죄책 감정 전부 흡수 금지.",
    ],
  },
  {
    binding: "faith_core",
    drawer_id: "gospel_core",
    query_mode: "inquiry_thematic_gospel_core",
    refs: ["1Cor.15.3", "1Cor.15.4", "Rom.1.16", "Mark.1.15"],
    one_liner_ko: "gospel_core — 1Cor.15.3–4 · Rom.1.16 [HYPO]",
    title_ko: "복음 핵심",
    bullets_ko: [
      "- **고린도전서 15.3–4:** 죽으심·장사·부활 — 복음의 내용.",
      "- **로마 1.16:** 복음은 모든 믿는 자에게 구원을 주시는 하나님의 능력.",
    ],
  },
  {
    binding: "angels",
    drawer_id: "angels_demons",
    query_mode: "inquiry_thematic_angels_demons",
    refs: ["Heb.1.14", "Ps.91.11", "Eph.6.12", "1Pet.5.8"],
    one_liner_ko: "angels_demons — Heb.1.14 · Eph.6.12 · 1Pet.5.8 [HYPO]",
    title_ko: "천사와 악한 영",
    bullets_ko: [
      "- **히브리서 1.14:** 섬기는 영 · 구원 얻을 후사들을 위하여.",
      "- **에베소 6.12 / 베드로전서 5.8:** 혈과 육에 대한 싸움이 아니요 · 근신하라.",
    ],
  },
  {
    binding: "family",
    drawer_id: "family_marriage",
    query_mode: "inquiry_thematic_family_marriage",
    refs: ["Gen.2.24", "Eph.5.25", "Eph.5.31", "Matt.19.5"],
    one_liner_ko: "family — Gen.2.24 · Eph.5.25 · Matt.19.5 [HYPO]",
    title_ko: "가정과 결혼",
    bullets_ko: [
      "- **창세기 2.24 / 마태 19.5:** 한 몸을 이룰지로다 · 결혼 축.",
      "- **에베소 5.25:** 아내 사랑 — 부모-자녀(Eph.6)와 질문을 섞지 않음.",
      "- 연애 궁합·결혼 시기 점 금지.",
    ],
  },
  {
    binding: "decalogue",
    drawer_id: "law_commands",
    query_mode: "inquiry_thematic_law_commands",
    refs: ["Exod.20.8", "Exod.20.11", "Acts.20.7", "1Cor.16.2"],
    one_liner_ko: "law_commands — Exod.20.8–11 · Acts.20.7 · 1Cor.16.2 [HYPO]",
    title_ko: "율법과 계명",
    bullets_ko: [
      "- **출애굽 20.8–11:** 안식일 계명 본문 축.",
      "- **사도행전 20.7 / 고린도전서 16.2:** 주간 첫날 모임·헌금 축(연구·비단정).",
    ],
  },
  {
    binding: "creation",
    drawer_id: "creation_origins",
    query_mode: "inquiry_thematic_creation_origins",
    refs: ["Gen.1.1", "Gen.1.27", "Gen.2.7", "Heb.11.3", "Col.1.16"],
    one_liner_ko: "creation — Gen.1–2 · Heb.11.3 · Col.1.16 [HYPO]",
    title_ko: "창조와 기원",
    bullets_ko: [
      "- **창세기 1–2 / 히브리서 11.3:** 창조 서사·믿음으로 세계가 지어진 줄 아노라.",
      "- **골로새 1.16:** 만물이 그 안에서 창조됨 — 과학 연대·진화 단정 금지.",
    ],
  },
  {
    binding: "love_enemy",
    drawer_id: "relationships_reconciliation",
    query_mode: "inquiry_thematic_relationships_reconciliation",
    refs: ["Matt.5.44", "Rom.12.18", "Matt.18.15", "Col.3.13"],
    one_liner_ko: "relationships — Matt.5.44 · Rom.12.18 · Matt.18.15 [HYPO]",
    title_ko: "관계와 화해",
    bullets_ko: [
      "- **마태 5.44 / 로마 12.18:** 원수를 사랑 · 할 수 있거든 화목하라.",
      "- **마태 18.15:** 형제에게 가서 권고하라.",
    ],
  },
  {
    binding: "comfort_sorrow",
    drawer_id: "comfort_lament",
    query_mode: "inquiry_thematic_comfort_sorrow",
    refs: [
      "2Cor.1.3",
      "2Cor.1.4",
      "Ps.34.18",
      "Ps.13.1",
      "Ps.22.1",
      "Matt.5.4",
      "Job.3.11",
    ],
    one_liner_ko: "comfort sorrow — Ps.13/22 lament · Job · 2Cor.1 · Ps.34 [HYPO]",
    title_ko: "위로와 탄식",
    bullets_ko: [
      "- **시편 13.1 / 22.1:** 탄식·버림받음 느낌도 기도로 올려질 수 있음.",
      "- **욥기 3.11 / 시편 34.18 / 마태 5.4:** 항변·애통 · 마음이 상한 자.",
      "- **고린도후서 1.3–4:** 위로의 하나님 (연구 참고 · 상담 대체 아님).",
    ],
  },
  {
    binding: "comfort_presence",
    drawer_id: "fear_anxiety",
    query_mode: "inquiry_thematic_comfort_presence",
    refs: ["Matt.6.25", "Matt.6.33", "Isa.41.10", "Phil.4.6"],
    one_liner_ko: "comfort presence — Matt.6.25 · Isa.41.10 · Phil.4.6 [HYPO]",
    title_ko: "두려움과 염려",
    bullets_ko: [
      "- **이사야 41.10 / 신명기 31.6:** 두려워 말라 · 떠나지 아니하리라.",
      "- **빌립보 4.6:** 아무것도 염려하지 말고.",
    ],
  },
  {
    binding: "job",
    drawer_id: "suffering_trials",
    query_mode: "inquiry_thematic_job",
    refs: ["Job.1.21", "Job.42.5", "Rom.5.3", "Jas.1.2"],
    one_liner_ko: "suffering — Job.1.21 · Rom.5.3 · Jas.1.2 [HYPO]",
    title_ko: "고난과 시험",
    bullets_ko: [
      "- **욥기 1.21 / 로마 5.3:** 주신 이도 여호와시니 · 환난 중 즐거워함.",
      "- **야고보 1.2:** 여러 가지 시험을 만나거든.",
    ],
  },
  {
    binding: "prayer",
    drawer_id: "prayer",
    query_mode: "inquiry_thematic_prayer_noun_domain",
    refs: ["Matt.6.9", "1Thess.5.17", "Phil.4.6", "Luke.11.1"],
    one_liner_ko: "prayer — Matt.6.9 · 1Thess.5.17 · Phil.4.6 [HYPO]",
    title_ko: "기도",
    bullets_ko: [
      "- **마태 6.9 / 누가 11.1:** 이렇게 기도하라 · 기도를 가르쳐 주옵소서.",
      "- **데살로니가전서 5.17:** 쉬지 말고 기도하라.",
    ],
  },
  {
    binding: "divination",
    drawer_id: "occult_divination_research",
    query_mode: "inquiry_thematic_divination_noun_domain",
    refs: ["Deut.18.10", "Deut.18.11", "Lev.19.31", "Isa.8.19"],
    one_liner_ko: "divination research — Deut.18.10–11 · Lev.19.31 [HYPO]",
    title_ko: "점술/주술 연구",
    bullets_ko: [
      "- **신명기 18.10–11 / 레위기 19.31:** 복술·신접 금지 축(연구).",
      "- 개인 점술·운세 맞춤 추천 아님.",
    ],
  },
  {
    binding: "speech",
    drawer_id: "speech_truth",
    query_mode: "inquiry_thematic_speech_guard",
    refs: ["Prov.12.22", "Eph.4.25", "Jas.3.5", "Prov.15.4"],
    one_liner_ko: "speech — Prov.12.22 · Eph.4.25 · Jas.3.5 [HYPO]",
    title_ko: "말과 진실",
    bullets_ko: [
      "- **잠언 12.22 / 에베소 4.25:** 거짓 입술은 여호와께 미움을 받아 · 참된 것을 말하라.",
      "- **야고보 3.5:** 혀는 작은 지체로되.",
    ],
  },
  {
    binding: "psalm23",
    drawer_id: "psalms_devotional",
    query_mode: "inquiry_thematic_psalm23",
    refs: ["Ps.23.1", "Ps.23.4", "Ps.1.2", "Ps.51.10"],
    one_liner_ko: "psalms — Ps.23 · Ps.1.2 · Ps.51.10 [HYPO]",
    title_ko: "시편 묵상",
    bullets_ko: [
      "- **시편 23:** 목자 동행 축.",
      "- **시편 1.2 / 51.10:** 율법을 주야로 묵상 · 정한 마음을 창조하소서.",
    ],
  },
];

/** All soft packs (remaining + gap). drawer_id lookup wins over binding. */
export const DRAWER_L2_SOFT_PACKS: DrawerL2PackDef[] = [
  ...DRAWER_L2_REMAINING_PACKS,
  ...DRAWER_L2_GAP_PACKS,
];

const BY_BINDING_REMAINING = new Map<string, DrawerL2PackDef>();
for (const p of DRAWER_L2_REMAINING_PACKS) {
  if (!BY_BINDING_REMAINING.has(p.binding)) BY_BINDING_REMAINING.set(p.binding, p);
}
const BY_DRAWER_REMAINING = new Map(
  DRAWER_L2_REMAINING_PACKS.map((p) => [p.drawer_id, p]),
);

/** Gap packs safe for late fallback (must not shadow gold-locked dedicated detectors). */
const LATE_GAP_SAFE = new Set([
  "jesus_person_work",
  "salvation_faith",
  "gospel_core",
  "angels_demons",
  "law_commands",
  "creation_origins",
  "relationships_reconciliation",
  "occult_divination_research",
  "psalms_devotional",
  "comfort_lament",
  "fear_anxiety",
  "suffering_trials",
  "family_marriage",
]);

const BY_DRAWER_LATE = new Map(
  DRAWER_L2_SOFT_PACKS.filter(
    (p) =>
      DRAWER_L2_REMAINING_PACKS.some((r) => r.drawer_id === p.drawer_id) ||
      LATE_GAP_SAFE.has(p.drawer_id),
  ).map((p) => [p.drawer_id, p]),
);

const BY_BINDING = new Map<string, DrawerL2PackDef>();
for (const p of DRAWER_L2_SOFT_PACKS) {
  if (!BY_BINDING.has(p.binding)) BY_BINDING.set(p.binding, p);
}
const BY_DRAWER = new Map(DRAWER_L2_SOFT_PACKS.map((p) => [p.drawer_id, p]));

export function getDrawerL2PackByBinding(binding: string | null | undefined): DrawerL2PackDef | null {
  if (!binding) return null;
  return BY_BINDING.get(binding) ?? null;
}

export function getDrawerL2PackByDrawerId(drawerId: string): DrawerL2PackDef | null {
  return BY_DRAWER.get(drawerId) ?? null;
}

export function buildDrawerL2PackBootstrap(
  query: string,
  pack: DrawerL2PackDef,
): {
  preset_id: string;
  query_mode: string;
  answer: string;
  verse_refs: string[];
  one_liner_ko: string;
  gap_ko: string;
  governance: string;
  citation_strength: "soft";
  honest_control_banner_ko: string;
  drawer_id: string;
  drawer_pack_bound: boolean;
} {
  const verse_refs = [...pack.refs];
  const qShort = query.trim().slice(0, 96);
  return {
    preset_id: FREEFORM_TOPICAL_PRESET_ID,
    query_mode: pack.query_mode,
    answer: [
      `「${qShort}」— ${pack.title_ko} 주제 연구 리포트입니다. [HYPO][NON_GATING] · send_gate: HOLD`,
      "",
      `### 본문 앵커 (citation lock · ${pack.drawer_id})`,
      `${verse_refs.join(" · ")}을 후보 좌표로 둡니다.`,
      ...pack.bullets_ko,
      "",
      "### 한계·주의",
      "- 본 답은 연구 참고이며 교리·의료·투자 확정이 아닙니다.",
    ].join("\n"),
    verse_refs,
    one_liner_ko: pack.one_liner_ko,
    gap_ko: `${pack.title_ko} 질문인데 일반/신앙 삼킴만이면 topic-fitness FAIL입니다.`,
    governance: "[HYPO][NON_GATING] · send_gate: HOLD · research_only · product_all_ok=false",
    citation_strength: "soft",
    honest_control_banner_ko: FREEFORM_WEAK_CITATION_BANNER_KO,
    drawer_id: pack.drawer_id,
    drawer_pack_bound: true,
  };
}

/**
 * Early path — remaining 16 only (no shadow of gold-locked prayer/speech/family packs).
 */
export function tryBuildRemainingDrawerL2Bootstrap(
  query: string,
  drawer: AskDrawerResolveV1,
): ReturnType<typeof buildDrawerL2PackBootstrap> | null {
  if (!drawer.matched) return null;
  const pack =
    BY_DRAWER_REMAINING.get(drawer.drawer_id) ||
    (drawer.pack_binding
      ? BY_BINDING_REMAINING.get(drawer.pack_binding) ?? null
      : null);
  if (!pack) return null;
  return buildDrawerL2PackBootstrap(query, pack);
}

/**
 * Late path — remaining + safe gap packs after dedicated detectors miss.
 * Excludes prayer/speech soft packs (gold batch2 family lock).
 */
export function tryBuildDrawerL2LateSoftBootstrap(
  query: string,
  drawer: AskDrawerResolveV1,
): ReturnType<typeof buildDrawerL2PackBootstrap> | null {
  if (!drawer.matched) return null;
  const pack = BY_DRAWER_LATE.get(drawer.drawer_id) ?? null;
  if (!pack) return null;
  return buildDrawerL2PackBootstrap(query, pack);
}

/** Alias kept for callers expecting full soft resolve via late-safe set. */
export const tryBuildDrawerL2SoftBootstrap = tryBuildDrawerL2LateSoftBootstrap;
