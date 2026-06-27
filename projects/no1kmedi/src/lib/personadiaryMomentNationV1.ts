/**
 * Parse daily guide package into user-facing "찰나의 나라" hero view.
 */
import type { DailyGuidePackage } from "./personadiaryDailyGuide";
import { sanitizeMomentLine } from "./personadiaryMomentDisplay";
import { buildMomentMealMenuRecommendation } from "./personadiaryMomentMealMenuV1";
import { derivePersonadiaryAcodeProfile, type DerivePersonadiaryAcodeOptions } from "./personadiaryAcodeProfileV1";

export type MomentNationView = {
  calendar_kst: string;
  city_label: string;
  fusion_line: string;
  fusion_line_cute: string;
  world_weather: string;
  world_headline: string;
  world_scene: string;
  world_scene_cute: string;
  me_line: string;
  me_line_cute: string;
  me_energy: string;
  acode_public: string;
  acode_title: string;
  acode_moment_tone: string;
  delight_meal: string;
  delight_outfit: string;
  /** @deprecated venue POI removed — always null/empty in meal-menu v1 */
  delight_poi: null;
  delight_poi_ko: string;
  pacing_hint: string;
  badge_ko: string;
};

const SKIP =
  /작전\(|Fact-Lock|Track A|적중|Brier|B-track|명리|4AI|코칭|페이싱|관측 모드|융합/i;

function sectionLines(pkg: DailyGuidePackage, id: string): string[] {
  const sec = (pkg.sections || []).find((s) => s.id === id);
  return (sec?.lines || []).map((l) => sanitizeMomentLine(String(l))).filter(Boolean);
}

function firstMatching(lines: string[], pred: (l: string) => boolean): string {
  return lines.find(pred) || "";
}

function blockBody(pkg: DailyGuidePackage, type: string): string {
  const block = (pkg.ui_blocks || []).find((b) => b.type === type);
  return block?.body_ko || "";
}

function humanizeLine(raw: string, fallback: string): string {
  let line = sanitizeMomentLine(raw);
  if (line.includes("→")) {
    line = (line.split("→").pop() || line).trim();
  }
  line = line
    .replace(/^융합[:\s]*/i, "")
    .replace(/판:\s*[^·]+·?/g, "")
    .replace(/오늘 한 줄[:\s]*/g, "")
    .trim();
  if (!line || line.length < 8 || SKIP.test(line)) return fallback;
  return line.slice(0, 140);
}

function cuteHeadline(raw: string): string {
  const t = sanitizeMomentLine(raw).replace(/^\d+\.\s*/, "");
  if (!t || SKIP.test(t)) return "오늘 세상 이야기 한 줄";
  const first = t.split(/[|·]/)[0]?.trim() || t;
  const short = first.split(/[.…]/)[0]?.trim().slice(0, 52) || first.slice(0, 52);
  return short.length < first.length ? `${short}…` : short;
}

function extractFusionLine(pkg: DailyGuidePackage): string {
  const hero = (pkg.ui_blocks || []).find((b) => b.type === "hero");
  const polished = pkg.moment_preset_polish_v1?.hero?.body_ko_polished?.trim();
  const raw = polished || hero?.body_ko || blockBody(pkg, "world_pulse");
  const lines = raw
    .split("\n")
    .map(sanitizeMomentLine)
    .filter((l) => l.length >= 12 && !SKIP.test(l));
  const fusion = lines.find((l) => l.includes("융합") || l.includes("→")) || lines[0];
  if (fusion) return fusion.slice(0, 220);
  const stream = sectionLines(pkg, "hypothesis_stream")[0];
  return stream.slice(0, 220) || "오늘은 세상과 나 사이에서 한 박자 쉬어 가도 괜찮아요.";
}

function extractHeadline(pkg: DailyGuidePackage): string {
  const worldLines = sectionLines(pkg, "world_pulse");
  const numbered = worldLines.find((l) => /^\d+\./.test(l));
  if (numbered) {
    return numbered.replace(/^\d+\.\s*/, "").slice(0, 120);
  }
  const fromBody = blockBody(pkg, "world_pulse")
    .split("\n")
    .map(sanitizeMomentLine)
    .find((l) => l.startsWith("1.") || l.includes("세상 헤드라인"));
  if (fromBody) {
    return fromBody.replace(/^1\.\s*/, "").slice(0, 120);
  }
  return "";
}

function extractSceneBand(pkg: DailyGuidePackage): string {
  const lines = sectionLines(pkg, "world_pulse");
  const scene = firstMatching(lines, (l) => l.includes("코스피") || l.includes("장면") || l.includes("거시"));
  if (scene) return scene.slice(0, 100);
  const fusion = extractFusionLine(pkg);
  const m = fusion.match(/판:\s*([^·]+)/);
  return m?.[1]?.trim().slice(0, 80) || "관측 모드";
}

export function buildMomentNationView(
  pkg: DailyGuidePackage | null,
  options?: DerivePersonadiaryAcodeOptions
): MomentNationView | null {
  if (!pkg?.ui_blocks?.length) return null;

  const lifestyle = sectionLines(pkg, "lifestyle");
  const mkm = sectionLines(pkg, "mkm_4ai");
  const myeongni = sectionLines(pkg, "myeongni");

  const weather = firstMatching(lifestyle, (l) => l.includes("날씨") || l.includes("°C"));
  const outfit = firstMatching(
    lifestyle,
    (l) => l.includes("스타일") || l.includes("컬러") || l.includes("입")
  );
  const meLine =
    firstMatching(myeongni, (l) => l.includes("오늘 한 줄")) ||
    myeongni[0] ||
    firstMatching(mkm, (l) => l.includes("코칭")) ||
    mkm[0] ||
    "";

  const energy =
    firstMatching(mkm, (l) => l.includes("AI") && l.length < 80) ||
    firstMatching(mkm, (l) => l.includes("보조")) ||
    "";

  const stream = sectionLines(pkg, "hypothesis_stream");
  const pacing =
    stream.find((l) => l.includes("페이싱") || l.includes("회복"))?.slice(0, 100) ||
    "말·결정은 짧게, 관측 우선 [가설]";

  const heroBadge =
    (pkg.ui_blocks || []).find((b) => b.type === "hero")?.badge_ko || "세상×나 · [가설]";

  const fusionRaw = extractFusionLine(pkg);
  const fusionCute = humanizeLine(
    fusionRaw,
    "오늘은 세상과 나 사이에서 한 박자 쉬어 가도 괜찮아요."
  );
  const mealCute = buildMomentMealMenuRecommendation(pkg, {
    surveyResponses: options?.surveyResponses,
  });
  const acode = derivePersonadiaryAcodeProfile(pkg, options);

  return {
    calendar_kst: pkg.calendar_kst || "—",
    city_label: pkg.city_default || "Seoul",
    fusion_line: fusionRaw,
    fusion_line_cute: fusionCute,
    world_weather: weather.slice(0, 80) || "날씨 맥락 준비 중",
    world_headline: extractHeadline(pkg) || "오늘의 헤드라인 한 줄",
    world_scene: extractSceneBand(pkg),
    world_scene_cute: cuteHeadline(extractHeadline(pkg)),
    me_line: meLine.slice(0, 140),
    me_line_cute: humanizeLine(meLine, "지금의 나 — 천천히 숨 고르기"),
    me_energy: energy.slice(0, 100),
    acode_public: acode.public_code,
    acode_title: acode.title_ko,
    acode_moment_tone: acode.moment_tone_ko,
    delight_meal: mealCute,
    delight_outfit: outfit.slice(0, 100) || "가볍고 통기 좋은 레이어",
    delight_poi: null,
    delight_poi_ko: "",
    pacing_hint: pacing,
    badge_ko: heroBadge,
  };
}
