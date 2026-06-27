export const personadiaryCopy = {
  brand: {
    name: "personadiary.com",
    tag: "preview",
  },
  seo: {
    title: "personadiary.com | AI 마음 일기 · 리플렉션 프리뷰",
    description:
      "A-Code·라이프·세상 맥락을 융합한 오늘의 마음 가이드 프리뷰. 의료·투자 조언이 아닙니다.",
  },
  dailyGuide: {
    conceptKo:
      "오늘의 마음 일기 — A-Code 12·라이프·세상 맥락 기반 가이드형 답변",
    apiPath: "/api/personadiary/daily-guide",
    feedbackApiPath: "/api/personadiary/feedback",
    packageSchema: "personadiary_daily_response_package_v1",
  },
  links: {
    demo: "/demo",
    observatory:
      "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1",
    contact: "mailto:hello@personadiary.com?subject=%5Bpersonadiary%5D%20%EC%82%AC%EC%A0%84%20%EC%95%8C%EB%A6%BC",
    waitlist: "/#waitlist",
    privacy: "/privacy",
    terms: "/terms",
  },
} as const;

/** Optional Tally/Google Form embed — set NEXT_PUBLIC_PERSONADIARY_WAITLIST_EMBED_URL */
export function personadiaryWaitlistEmbedUrl(): string | undefined {
  const v = process.env.NEXT_PUBLIC_PERSONADIARY_WAITLIST_EMBED_URL?.trim();
  return v || undefined;
}
