/**
 * PersonaDiary moment intent + response (Phase B) — TS mirror of scripts/*_v1.py
 */
import type { DailyGuidePackage, DailyGuideSection } from "./personadiaryDailyGuide";
import {
  derivePersonadiaryAcodeProfile,
  type PersonadiaryAcodePersonaV1,
} from "./personadiaryAcodeProfileV1";
import { buildMomentMealMenuRecommendation } from "./personadiaryMomentMealMenuV1";
import {
  INTENT_KEYWORDS,
  INTENT_PRIORITY,
  INTENT_WEIGHTS,
  isNonGatingSection,
  PROPHECY_VOTE_NONE,
  SECTION_TITLES,
  type MomentIntentFromSsot,
} from "./personadiaryMomentIntentWeightsV1";
import {
  resolveMomentBundle,
  type MomentBundleResolved,
} from "./personadiaryMomentBundleV1";

export type MomentIntent = MomentIntentFromSsot;

const PRIORITY = INTENT_PRIORITY;

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
  prophecy_vote: "none";
  regime_field: "regime_personadiary_moment_exploration";
  query_text: string;
  intent: MomentIntent;
  intent_classification: IntentClassification;
  calendar_kst?: string;
  city_default?: string;
  profile_id: string;
  cards: MomentCard[];
  summary_ko: string;
  acode_persona?: PersonadiaryAcodePersonaV1;
  summary_ko_polished?: string | null;
  polish_meta?: MomentPolishMeta;
  disclaimer_ko: string;
  generated_at_utc: string;
  moment_bundle: MomentBundleResolved;
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
  classification?: IntentClassification,
  options?: { requestProfileId?: string | null; surveyResponses?: Record<string, number> }
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
      badge_ko: isNonGatingSection(sid) ? "[NON_GATING][가설]" : "[가설]",
    });
  }

  let summary_ko = "";
  if (intent === "meal") {
    summary_ko = buildMomentMealMenuRecommendation(pkg, {
      surveyResponses: options?.surveyResponses,
    });
    if (!summary_ko) {
      summary_ko = firstMealSummary(cards);
    }
  }
  if (!summary_ko) {
    const summaryParts = cards
      .slice(0, 2)
      .map((c) => c.body_ko.split("\n")[0]?.slice(0, 120))
      .filter(Boolean);
    summary_ko =
      summaryParts.join(" · ") || "오늘 가이드에서 순간 성찰만 비춥니다.";
  }

  const acodePersona = derivePersonadiaryAcodeProfile(pkg, {
    surveyResponses: options?.surveyResponses,
  });
  const resolvedProfileId =
    options?.requestProfileId?.trim() ||
    pkg.profile_id ||
    "commander";

  const base: MomentResponse = {
    schema: "personadiary_moment_response_v1",
    product: "personadiary.com",
    hypothesis_tier: "B",
    preview_only: true,
    non_gating: true,
    lane: "research_only",
    prophecy_vote: PROPHECY_VOTE_NONE,
    regime_field: "regime_personadiary_moment_exploration",
    query_text: query.trim().slice(0, 500),
    intent,
    intent_classification: clf,
    calendar_kst: pkg.calendar_kst,
    city_default: pkg.city_default,
    profile_id: resolvedProfileId,
    cards: cards.slice(0, 4),
    summary_ko: summary_ko.slice(0, 400),
    acode_persona: acodePersona,
    disclaimer_ko:
      pkg.disclaimer_ko ||
      "[가설]·[NON_GATING] 마음돌봄·순간 가이드 전용. preview_only.",
    generated_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    moment_bundle: resolveMomentBundle(
      pkg,
      intent,
      pkg.calendar_kst || new Date().toISOString().slice(0, 10)
    ),
  };
  return applyPresetPolish(pkg, base, query);
}
