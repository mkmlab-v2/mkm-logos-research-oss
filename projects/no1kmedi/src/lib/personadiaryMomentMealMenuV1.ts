/**
 * PersonaDiary moment meal menu v1 — menu type only (no venue/POI).
 * Blends weather, constitution hints, news mood, and "me right now" [HYPO].
 */
import type { DailyGuidePackage } from "./personadiaryDailyGuide";
import { sanitizeMomentLine } from "./personadiaryMomentDisplay";
import { derivePersonadiaryAcodeProfile } from "./personadiaryAcodeProfileV1";

export type MomentMealMenuOptions = {
  surveyResponses?: Record<string, number>;
};

export const MOMENT_MEAL_MENU_SCHEMA = "personadiary_moment_meal_menu_v1" as const;

const MENU_KEYWORDS = [
  "국밥",
  "곰탕",
  "삼계탕",
  "닭곰탕",
  "미역",
  "찌개",
  "전골",
  "비빔밥",
  "냉면",
  "콩국수",
  "샐러드",
  "죽",
  "덮밥",
  "우동",
  "파스타",
  "칼국수",
  "수제비",
];

const LOCATION_NOISE =
  /[가-힣]+역\s*(근처|인근)?|근처\s*골목[^·—]*/g;

export function stripLocationFromMealText(line: string): string {
  let s = sanitizeMomentLine(line);
  s = s.replace(LOCATION_NOISE, "");
  s = s.replace(/골목\s*[-—–]\s*/g, "");
  s = s.replace(/맛집\s*[:·]\s*/gi, "");
  s = s.replace(/\s{2,}/g, " ").replace(/^[-·—]\s*/, "").trim();
  return s;
}

function sectionLines(pkg: DailyGuidePackage, id: string): string[] {
  const sec = (pkg.sections || []).find((s) => s.id === id);
  return (sec?.lines || []).map((l) => sanitizeMomentLine(String(l))).filter(Boolean);
}

function extractMenuTypes(...lines: string[]): string {
  const found = new Set<string>();
  for (const line of lines) {
    const clean = stripLocationFromMealText(line);
    for (const kw of MENU_KEYWORDS) {
      if (clean.includes(kw)) found.add(kw);
    }
  }
  if (found.size) return [...found].slice(0, 3).join("·");
  const base = stripLocationFromMealText(
    lines.find((l) => /점심|메뉴|추천|국밥|곰탕/.test(l)) || ""
  );
  if (base.length >= 4) return base.replace(/^점심[:\s]*/i, "").slice(0, 36);
  return "따뜻한 국물";
}

function weatherMealHint(weather: string): string | null {
  if (/무더위|폭염|찌는|3[3-9]°|더움|더워|무덥/.test(weather)) {
    return "더위엔 맑은 국물·가벼운 단백질";
  }
  if (/비|장마|흐림|우산/.test(weather)) {
    return "비 오는 날엔 따뜻한 찌개·전골";
  }
  if (/쌀쌀|선선|바람|일교차/.test(weather)) {
    return "쌀쌀하면 구수한 국밥·찜";
  }
  return null;
}

function acodeMealHint(
  pkg: DailyGuidePackage,
  surveyResponses?: Record<string, number>
): string | null {
  const acode = derivePersonadiaryAcodeProfile(pkg, { surveyResponses });
  return `${acode.public_code} ${acode.title_ko} · ${acode.meal_tone_ko}`;
}

function newsMealHint(headline: string): string | null {
  if (!headline) return null;
  if (/코스피|비트코인|ETF|금리|불안|급락|변동|리플|XRP/.test(headline)) {
    return "뉴스가 복잡할 땐 편안한 한 그릇";
  }
  return null;
}

function momentMealHint(meLine: string): string | null {
  const m = stripLocationFromMealText(meLine);
  if (!m || m.length < 6) return null;
  if (/숨|쉬|회복|피곤|지침/.test(m)) return "찰나엔 속 편한 메뉴";
  if (/관계|마음|대화/.test(m)) return "마음 쉬며 즐기기 좋은 담백 메뉴";
  return null;
}

/** User-facing one-liner: menu types + why (no place names). */
export function buildMomentMealMenuRecommendation(
  pkg: DailyGuidePackage,
  options?: MomentMealMenuOptions
): string {
  const lifestyle = sectionLines(pkg, "lifestyle");
  const world = sectionLines(pkg, "world_pulse");
  const mkm = sectionLines(pkg, "mkm_4ai");
  const myeongni = sectionLines(pkg, "myeongni");

  const weather = lifestyle.find((l) => l.includes("날씨") || l.includes("°C")) || "";
  const mealLine =
    lifestyle.find((l) => /점심|메뉴|추천|국밥|곰탕/.test(l)) || "";
  const headline =
    world.find((l) => /^\d+\./.test(l))?.replace(/^\d+\.\s*/, "") || world[0] || "";
  const meLine =
    myeongni.find((l) => l.includes("오늘 한 줄")) ||
    mkm.find((l) => l.includes("코칭")) ||
    myeongni[0] ||
    "";

  const menuTypes = extractMenuTypes(mealLine, mkm.join("\n"), lifestyle.join("\n"));
  const reasons = [
    weatherMealHint(weather),
      acodeMealHint(pkg, options?.surveyResponses),
    newsMealHint(headline),
    momentMealHint(meLine),
  ].filter(Boolean) as string[];

  const why =
    reasons.length > 0
      ? reasons.slice(0, 2).join(" · ")
      : "날씨·오늘 흐름에 맞춘 메뉴";
  return stripLocationFromMealText(`${menuTypes} — ${why}`).slice(0, 118);
}
