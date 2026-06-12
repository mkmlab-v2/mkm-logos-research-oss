export type HubDiscoverLocale = "ko" | "en";

export const HUB_DISCOVER_COPY: Record<
  HubDiscoverLocale,
  {
    title: string;
    lead: string;
    placeholder: string;
    submit: string;
    routingNote: string;
    b2bPrefix: string;
    b2bLink: string;
    localeToggle: string;
    validationMissing: string;
  }
> = {
  ko: {
    title: "가장 중요한 질문을 한 문장으로",
    lead: "원퀘스천 엔진은 단발 리포트로 완결됩니다. 무한 대화가 아닙니다.",
    placeholder: "가장 중요한 질문을 한 문장으로",
    submit: "라우팅 · 리포트로 이동",
    routingNote: "허브 내부 LLM 없음 — 규칙 라우터가 mkmlife·플러그인으로만 분기합니다.",
    b2bPrefix: "B2B ·",
    b2bLink: "AI 맞춤·가드 (WTT Persona OS)",
    localeToggle: "EN",
    validationMissing: "질문을 입력하거나 위 의도 칩을 선택해 주세요. 빈 제출로 외부 사이트로 이동하지 않습니다.",
  },
  en: {
    title: "Ask your one most important question",
    lead: "One-question engine ends in a single report — not endless chat.",
    placeholder: "Ask your one most important question",
    submit: "Route · open report flow",
    routingNote: "No hub LLM — rule router branches to mkmlife and plugins only.",
    b2bPrefix: "B2B ·",
    b2bLink: "Governed customization (WTT Persona OS)",
    localeToggle: "KO",
    validationMissing:
      "Enter a question or pick an intent chip above. Empty submit will not redirect externally.",
  },
};
