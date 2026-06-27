"use client";

import { personadiaryWaitlistEmbedUrl } from "@/content/personadiaryCopy";

const FREE_FEATURES = [
  "오늘의 찰나의 나라 카드",
  "찰나 질문 하루 3회",
  "행운·리추얼 카드 1장",
  "로컬 일기 기지 (IndexedDB)",
] as const;

const PLUS_FEATURES = [
  "찰나 질문 무제한",
  "메뉴·리듬 확장 팩",
  "페르소나 비주얼 카드 월간",
  "AI BGM 클립 라이브러리",
] as const;

export function PersonadiaryPlusTeaser() {
  const waitlistHref = personadiaryWaitlistEmbedUrl() || "#waitlist";

  return (
    <section
      className="pd-plus-teaser"
      aria-labelledby="pd-plus-title"
      data-testid="pd-plus-teaser"
    >
      <span className="pd-plus-ssot" hidden aria-hidden>
        pd-plus-teaser
      </span>
      <div className="pd-premium-section-inner">
        <p className="pd-ios-group-label" id="pd-plus-title">
          Persona Diary Plus · 사전 알림
        </p>
        <p className="pd-plus-lead">
          결제·mkmlife 합선 없음 — Plus는 별도 SKU로 준비 중입니다. 지금은 프리뷰 무료 체험만
          제공합니다.
        </p>
        <div className="pd-plus-grid">
          <article className="pd-glass pd-plus-card pd-plus-card--free">
            <h3>Free · 지금</h3>
            <ul>
              {FREE_FEATURES.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <p className="pd-plus-price">₩0 · preview_only</p>
          </article>
          <article className="pd-glass pd-plus-card pd-plus-card--plus">
            <h3>Plus · 준비 중</h3>
            <ul>
              {PLUS_FEATURES.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <p className="pd-plus-price">₩4,900/월 · 가설 · SEND_GATE: HOLD</p>
          </article>
        </div>
        <a className="btn btn-primary" href={waitlistHref}>
          Plus 사전 알림 받기
        </a>
        <p className="pd-plus-muted">의료·투자·실매매 조언 아님 · 운세·적중% 단정 없음</p>
      </div>
    </section>
  );
}
