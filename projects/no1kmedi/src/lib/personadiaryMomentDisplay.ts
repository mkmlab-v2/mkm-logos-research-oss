/**
 * User-facing formatting for PersonaDiary moment results (hide dev/schema noise).
 */
import type { MomentCard, MomentIntent } from "./personadiaryMoment";

const INTENT_HEADLINE: Record<MomentIntent, string> = {
  meal: "오늘 점심 한 줄",
  weather_fit: "오늘 입기 좋은 톤",
  mood: "지금 마음 돌보기",
  world_me: "세상과 나",
  reflect: "가벼운 성찰",
};

const SKIP_LINE =
  /작전\(|Fact-Lock|Track A|스키마|research_only|preview_only|무관\s*$/i;

export function intentHeadlineKo(intent: MomentIntent): string {
  return INTENT_HEADLINE[intent] || "순간 가이드";
}

export function sanitizeMomentLine(line: string): string {
  let s = line.trim();
  s = s.replace(/\[(?:가설|NON_GATING|HYPO)[^\]]*\]/gi, "").trim();
  s = s.replace(/\s*·\s*/g, " · ").replace(/^·\s*|\s*·$/g, "");
  return s;
}

function mealBulletScore(line: string): number {
  const primary = ["점심", "메뉴", "국밥", "곰탕", "맛집", "피하기", "저녁"];
  for (let i = 0; i < primary.length; i++) {
    if (line.includes(primary[i])) return 100 - i;
  }
  if (line.includes("날씨") || line.includes("컬러") || line.includes("스타일")) return 10;
  return 0;
}

export function extractMomentBullets(
  body: string,
  max = 3,
  intent?: MomentIntent
): string[] {
  const raw = body
    .split("\n")
    .map(sanitizeMomentLine)
    .filter((ln) => ln.length >= 6 && !SKIP_LINE.test(ln));
  const lines =
    intent === "meal"
      ? [...raw].sort((a, b) => mealBulletScore(b) - mealBulletScore(a))
      : raw;
  if (lines.length) return lines.slice(0, max);
  const fallback = sanitizeMomentLine(body.replace(/\n/g, " "));
  return fallback ? [fallback.slice(0, 160)] : [];
}

export function formatUserSummary(summary: string): string {
  const parts = summary
    .split("·")
    .map(sanitizeMomentLine)
    .filter((p) => p.length >= 10 && !SKIP_LINE.test(p));
  if (parts[0]) return parts[0].slice(0, 200);
  const flat = sanitizeMomentLine(summary);
  return flat.slice(0, 200) || "오늘 맥락에서 가볍게 제안드립니다.";
}

export type DisplayMomentCard = {
  title_ko: string;
  bullets: string[];
};

export function toDisplayMomentCards(
  cards: MomentCard[],
  maxCards = 2,
  intent?: MomentIntent
): DisplayMomentCard[] {
  return cards.slice(0, maxCards).map((c) => ({
    title_ko: c.title_ko,
    bullets: extractMomentBullets(c.body_ko, 3, intent),
  }));
}

export const USER_MOMENT_DISCLAIMER =
  "미리보기 가이드입니다. 의료·투자·처방 조언을 대체하지 않습니다.";

export function sanitizeGuideBody(text: string, maxLen = 160): string {
  const stripped = text
    .replace(/\[(?:가설|NON_GATING)[^\]]*\]/gi, "")
    .replace(/작전\([^)]*\)/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const parts = stripped
    .split("·")
    .map((p) => p.trim())
    .filter((p) => p.length >= 8 && !SKIP_LINE.test(p) && !p.includes("작전"));
  const clean = (parts.length ? parts.slice(0, 2).join(" · ") : stripped).trim();
  if (clean.length <= maxLen) return clean;
  return `${clean.slice(0, maxLen).trimEnd()}…`;
}
