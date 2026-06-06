/**
 * PersonaDiary moment intent + response (Phase B) — TS mirror of scripts/*_v1.py
 */
import type { DailyGuidePackage, DailyGuideSection } from "./personadiaryDailyGuide";

export type MomentIntent =
  | "meal"
  | "weather_fit"
  | "mood"
  | "world_me"
  | "reflect";

const INTENT_KEYWORDS: Record<Exclude<MomentIntent, "reflect">, string[]> = {
  meal: [
    "점심",
    "저녁",
    "아침",
    "뭐 먹",
    "뭘 먹",
    "식사",
    "메뉴",
    "맛집",
    "국밥",
    "배고",
    "먹을까",
    "먹지",
    "라면",
    "밥",
  ],
  weather_fit: [
    "날씨",
    "옷",
    "입을",
    "입어",
    "컬러",
    "색",
    "따뜻",
    "춥",
    "더워",
    "우산",
    "비",
    "외출",
    "코디",
  ],
  mood: [
    "기분",
    "마음",
    "불안",
    "우울",
    "스트레스",
    "피곤",
    "슬프",
    "걱정",
    "지침",
    "무기력",
    "짜증",
    "외로",
  ],
  world_me: [
    "뉴스",
    "세상",
    "코스피",
    "비트코인",
    "btc",
    "시장",
    "헤드라인",
    "정치",
    "거시",
    "경제",
    "속보",
  ],
};

// world_me before mood — news-linked anxiety routes to world_me, not pure mood
const PRIORITY: Exclude<MomentIntent, "reflect">[] = [
  "meal",
  "weather_fit",
  "world_me",
  "mood",
];

const INTENT_WEIGHTS: Record<MomentIntent, Record<string, number>> = {
  meal: { lifestyle: 0.45, myeongni: 0.35, mkm_4ai: 0.15, logos_anchor: 0.05 },
  weather_fit: { lifestyle: 0.5, mkm_4ai: 0.3, myeongni: 0.15, logos_anchor: 0.05 },
  mood: {
    mkm_4ai: 0.35,
    myeongni: 0.25,
    logos_anchor: 0.25,
    user_condition: 0.15,
  },
  world_me: {
    world_pulse: 0.45,
    hypothesis_stream: 0.25,
    myeongni: 0.2,
    logos_anchor: 0.1,
  },
  reflect: {
    myeongni: 0.25,
    mkm_4ai: 0.2,
    lifestyle: 0.2,
    world_pulse: 0.2,
    logos_anchor: 0.15,
  },
};

const SECTION_TITLES: Record<string, string> = {
  myeongni: "명리 한 줄",
  mkm_4ai: "마음 에너지 (4AI)",
  lifestyle: "라이프·날씨",
  logos_anchor: "성경 앵커",
  world_pulse: "찰나의 나라",
  hypothesis_stream: "초론 스트림",
  user_condition: "컨디션 틸트",
};

const MEAL_PRIMARY = [
  "점심 추천",
  "점심:",
  "저녁",
  "아침",
  "메뉴",
  "국밥",
  "곰탕",
  "맛집",
  "피하기",
];
const MEAL_SECONDARY = ["날씨", "컬러", "스타일", "퍼스널"];

function mealLineScore(line: string): number {
  for (let i = 0; i < MEAL_PRIMARY.length; i++) {
    if (line.includes(MEAL_PRIMARY[i])) return 200 - i;
  }
  for (let i = 0; i < MEAL_SECONDARY.length; i++) {
    if (line.includes(MEAL_SECONDARY[i])) return 80 - i;
  }
  return 0;
}

export type IntentClassification = {
  intent: MomentIntent;
  score: number;
  matched_keywords: string[];
  lane: "research_only";
  hypothesis_tier: "B";
};

export type MomentCard = {
  section_id: string;
  lens: string;
  title_ko: string;
  body_ko: string;
  weight: number;
  badge_ko: string;
};

export type MomentPolishMeta = {
  lane?: string;
  hypothesis_tier?: string;
  backend?: string;
  applied?: boolean;
  reason?: string;
  source?: string;
};

export type MomentResponse = {
  schema: "personadiary_moment_response_v1";
  product: "personadiary.com";
  hypothesis_tier: "B";
  preview_only: true;
  non_gating: true;
  lane: "research_only";
  regime_field: "regime_personadiary_moment_exploration";
  query_text: string;
  intent: MomentIntent;
  intent_classification: IntentClassification;
  calendar_kst?: string;
  city_default?: string;
  profile_id: string;
  cards: MomentCard[];
  summary_ko: string;
  summary_ko_polished?: string | null;
  polish_meta?: MomentPolishMeta;
  disclaimer_ko: string;
  generated_at_utc: string;
};

function applyPresetPolish(
  pkg: DailyGuidePackage,
  moment: MomentResponse,
  query: string
): MomentResponse {
  const block = pkg.moment_preset_polish_v1;
  const preset = block?.presets?.[moment.intent];
  if (!preset?.summary_ko_polished) return moment;
  const canonical = (preset.canonical_query || "").trim();
  if (!canonical || query.trim() !== canonical) return moment;
  return {
    ...moment,
    summary_ko_polished: preset.summary_ko_polished,
    polish_meta: {
      lane: "research_only",
      hypothesis_tier: "B",
      backend: "ollama_preset_cache",
      applied: true,
      source: "moment_preset_polish_v1",
      ...(preset.polish_meta as MomentPolishMeta | undefined),
    },
  };
}

function normalize(text: string): string {
  return text.trim().toLowerCase().replace(/\s+/g, " ");
}

export function classifyIntent(query: string): IntentClassification {
  const norm = normalize(query);
  if (!norm) {
    return {
      intent: "reflect",
      score: 0,
      matched_keywords: [],
      lane: "research_only",
      hypothesis_tier: "B",
    };
  }

  const scores: Record<Exclude<MomentIntent, "reflect">, number> = {
    meal: 0,
    weather_fit: 0,
    mood: 0,
    world_me: 0,
  };
  const matched: Record<Exclude<MomentIntent, "reflect">, string[]> = {
    meal: [],
    weather_fit: [],
    mood: [],
    world_me: [],
  };

  for (const intent of PRIORITY) {
    for (const kw of INTENT_KEYWORDS[intent]) {
      if (norm.includes(kw)) {
        scores[intent] += 1;
        matched[intent].push(kw);
      }
    }
  }

  const best = Math.max(...Object.values(scores));
  if (best === 0) {
    return {
      intent: "reflect",
      score: 0,
      matched_keywords: [],
      lane: "research_only",
      hypothesis_tier: "B",
    };
  }

  const winner = PRIORITY.find((i) => scores[i] === best)!;
  return {
    intent: winner,
    score: best,
    matched_keywords: matched[winner].slice(0, 5),
    lane: "research_only",
    hypothesis_tier: "B",
  };
}

function pickLines(lines: string[], intent: MomentIntent): string[] {
  if (!lines.length) return [];
  if (intent === "meal") {
    const scored = [...lines].sort(
      (a, b) => mealLineScore(b) - mealLineScore(a) || lines.indexOf(a) - lines.indexOf(b)
    );
    const picked = scored.filter((ln) => mealLineScore(ln) > 0);
    return (picked.length ? picked : lines).slice(0, 4);
  }
  if (intent === "weather_fit") {
    const picked = lines.filter((ln) =>
      ["날씨", "컬러", "스타일", "옷", "°", "퍼스널"].some((k) => ln.includes(k))
    );
    return (picked.length ? picked : lines).slice(0, 4);
  }
  return lines.slice(0, 4);
}

function firstMealSummary(cards: MomentCard[]): string {
  for (const card of cards) {
    if (card.section_id !== "lifestyle") continue;
    for (const ln of card.body_ko.split("\n")) {
      const t = ln.trim();
      if (["점심", "메뉴", "국밥", "곰탕", "저녁", "맛집"].some((k) => t.includes(k))) {
        return t.slice(0, 200);
      }
    }
  }
  return "";
}

function sectionBody(
  sec: DailyGuideSection | undefined,
  intent: MomentIntent
): string {
  if (!sec?.lines?.length) return "";
  const lines = sec.lines.map((l) => String(l).trim()).filter(Boolean);
  return pickLines(lines, intent).join("\n").slice(0, 480);
}

export function assembleMomentResponse(
  pkg: DailyGuidePackage,
  query: string,
  classification?: IntentClassification
): MomentResponse {
  const clf = classification || classifyIntent(query);
  const intent = clf.intent;
  const weights = INTENT_WEIGHTS[intent];
  const secMap = new Map<string, DailyGuideSection>();
  for (const sec of pkg.sections || []) {
    if (sec?.id) secMap.set(sec.id, sec);
  }

  const cards: MomentCard[] = [];
  const sorted = Object.entries(weights).sort((a, b) => b[1] - a[1]);
  for (const [sid, weight] of sorted) {
    const body = sectionBody(secMap.get(sid), intent);
    if (!body) continue;
    cards.push({
      section_id: sid,
      lens: sid,
      title_ko: SECTION_TITLES[sid] || sid,
      body_ko: body,
      weight: Math.round(weight * 100) / 100,
      badge_ko: sid === "logos_anchor" ? "[NON_GATING][가설]" : "[가설]",
    });
  }

  let summary_ko = "";
  if (intent === "meal") {
    summary_ko = firstMealSummary(cards);
  }
  if (!summary_ko) {
    const summaryParts = cards
      .slice(0, 2)
      .map((c) => c.body_ko.split("\n")[0]?.slice(0, 120))
      .filter(Boolean);
    summary_ko =
      summaryParts.join(" · ") || "오늘 가이드에서 순간 성찰만 비춥니다.";
  }

  const base: MomentResponse = {
    schema: "personadiary_moment_response_v1",
    product: "personadiary.com",
    hypothesis_tier: "B",
    preview_only: true,
    non_gating: true,
    lane: "research_only",
    regime_field: "regime_personadiary_moment_exploration",
    query_text: query.trim().slice(0, 500),
    intent,
    intent_classification: clf,
    calendar_kst: pkg.calendar_kst,
    city_default: pkg.city_default,
    profile_id: pkg.profile_id || "commander",
    cards: cards.slice(0, 4),
    summary_ko: summary_ko.slice(0, 400),
    disclaimer_ko:
      pkg.disclaimer_ko ||
      "[가설]·[NON_GATING] 마음돌봄·순간 가이드 전용. preview_only.",
    generated_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
  };
  return applyPresetPolish(pkg, base, query);
}
