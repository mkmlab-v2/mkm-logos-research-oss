"use client";

import Link from "next/link";
import { personadiaryCopy } from "@/content/personadiaryCopy";
import { PersonadiaryMagicOrb } from "./PersonadiaryMagicOrb";
import { PersonadiaryDailyGuideCards } from "./PersonadiaryDailyGuideCards";
import { PersonadiaryReflectTeaser } from "./PersonadiaryReflectTeaser";
import { PersonadiaryDailyGuideProvider } from "./usePersonadiaryDailyGuide";

export function PersonadiaryPremiumHome() {
  return (
    <>
      <section className="pd-premium-hero" aria-labelledby="personadiary-title">
        <div className="pd-premium-hero-bg" aria-hidden="true" />
        <div className="pd-premium-hero-inner">
          <div className="pd-premium-hero-copy">
            <span className="pd-premium-eyebrow">Persona Diary · Open Beta</span>
            <h1 id="personadiary-title">오늘의 마음을, 빛의 구슬에 남기다</h1>
            <p className="pd-premium-lead">
              AI 마음 일기·하루 리플렉션 프리뷰. 평온을 돕는 가이드형 성찰
              셸이며, 의료·투자·처방 조언을 대체하지 않습니다.
            </p>
            <div className="pd-premium-cta">
              <a className="btn btn-primary" href={personadiaryCopy.links.waitlist}>
                사전 알림 등록
              </a>
              <Link className="btn btn-ghost" href={personadiaryCopy.links.demo}>
                전체 데모 체험
              </Link>
            </div>
          </div>
          <div className="pd-premium-hero-visual pd-glass">
            <PersonadiaryMagicOrb size={280} />
          </div>
        </div>
      </section>

      <section
        className="pd-premium-reflect-section"
        aria-labelledby="pd-reflect-home-title"
      >
        <div className="pd-premium-section-inner">
          <h2 id="pd-reflect-home-title">지금 이 순간, 가볍게 성찰해 보기</h2>
          <p className="pd-premium-section-lead">
            홈에서 바로 체험할 수 있는 미리보기입니다. 더 깊은 인터랙션은
            콘셉트 데모에서 이어집니다.
          </p>
          <div className="pd-premium-reflect-grid">
            <div className="pd-glass pd-premium-reflect-panel">
              <PersonadiaryDailyGuideProvider>
                <PersonadiaryReflectTeaser />
                <PersonadiaryDailyGuideCards />
              </PersonadiaryDailyGuideProvider>
            </div>
            <aside className="pd-glass pd-premium-aside">
              <h3>마음돌봄 셸</h3>
              <p>
                시각·청각 리플렉션만 제공합니다. 일기 영속 저장·결제·임상 연동은
                오픈베타 범위 밖입니다.
              </p>
              <p className="pd-premium-aside-muted">
                인프라·압축 수치는 B2B 도메인(jema-ai.com · jemaai.cloud)에만
                노출합니다.
              </p>
            </aside>
          </div>
        </div>
      </section>

      <section
        className="pd-premium-pillars"
        aria-labelledby="pd-pillars-title"
      >
        <div className="pd-premium-section-inner">
          <h2 id="pd-pillars-title">프리뷰 검증 축</h2>
          <div className="pd-pillar-grid">
            <article className="pd-glass pd-pillar-card">
              <span className="pd-pillar-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2M12 20v2M2 12h2M20 12h2" />
                </svg>
              </span>
              <h3>찰나의 나</h3>
              <p>
                매일 한 줄 리플렉션으로 기록 습관과 감정·상태 리캡을 보조합니다.
              </p>
            </article>
            <article className="pd-glass pd-pillar-card">
              <span className="pd-pillar-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 3c-4 0-7 2.5-7 6 0 5 7 12 7 12s7-7 7-12c0-3.5-3-6-7-6z" />
                </svg>
              </span>
              <h3>개인화 콘텐츠</h3>
              <p>
                스트레스·루틴 신호를 바탕으로 오디오·비주얼 추천을 실험합니다.
              </p>
            </article>
            <article className="pd-glass pd-pillar-card">
              <span className="pd-pillar-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="4" y="4" width="16" height="16" rx="3" />
                  <path d="M8 12h8M12 8v8" />
                </svg>
              </span>
              <h3>모먼트 수집</h3>
              <p>
                카드형 수집·공유는 정책·법무·정산 게이트 이후 별도 검증합니다.
              </p>
            </article>
          </div>
        </div>
      </section>
    </>
  );
}
