"use client";

import Link from "next/link";
import { personadiaryPublicPath } from "@/lib/personadiaryMobileOpsV1";
import { surveyResponsesForAcodeDerive } from "@/lib/personadiaryConsumerProfileV1";
import { buildMomentNationView } from "@/lib/personadiaryMomentNationV1";
import { usePersonadiaryDailyGuide } from "./usePersonadiaryDailyGuide";

export function PersonadiaryMomentNationHero() {
  const { pkg, loading, error } = usePersonadiaryDailyGuide();
  const surveyResponses = surveyResponsesForAcodeDerive();
  const view = buildMomentNationView(pkg, { surveyResponses });
  const opsHref = personadiaryPublicPath("/ops");

  return (
    <section
      className="pd-moment-nation-hero"
      aria-labelledby="pd-moment-nation-title"
      data-testid="pd-moment-nation-hero"
    >
      <div className="pd-moment-nation-glow" aria-hidden />
      <div className="pd-premium-section-inner pd-moment-nation-inner">
        <span className="pd-moment-nation-eyebrow">
          Persona Diary · 찰나의 나라 · {view?.calendar_kst || "오늘"}
        </span>
        <h1 id="pd-moment-nation-title">세상 속의 나</h1>
        <p className="pd-moment-nation-sub">
          뉴스 · 날씨 · 거시와 지금의 내가 만나는, 오늘 이 순간만의 나라
        </p>
        <span className="pd-moment-nation-poi-ssot" hidden aria-hidden>
          moment-meal-menu-v1
        </span>
        <span className="pd-moment-nation-acode-ssot" hidden aria-hidden>
          pd-acode-persona-v1
        </span>

        {loading ? (
          <p className="pd-moment-nation-loading">찰나의 판을 읽는 중…</p>
        ) : error || !view ? (
          <p className="pd-moment-nation-fallback">
            오늘의 찰나 카드는 준비 중이에요. 아래에서 순간 질문으로 먼저 체험해 보세요.
          </p>
        ) : (
          <>
            <article className="pd-moment-nation-card pd-glass">
              <p className="pd-moment-nation-fusion">{view.fusion_line_cute}</p>
              <div className="pd-moment-nation-split">
                <div className="pd-moment-nation-pane pd-moment-nation-pane--world">
                  <span className="pd-moment-nation-pane-label">세상</span>
                  <p>{view.world_weather}</p>
                  <p className="pd-moment-nation-headline">{view.world_scene_cute}</p>
                </div>
                <div className="pd-moment-nation-pane pd-moment-nation-pane--me">
                  <span className="pd-moment-nation-pane-label">지금의 나</span>
                  <p>{view.me_line_cute}</p>
                  <p className="pd-moment-nation-acode">
                    {view.acode_public} · {view.acode_title}
                  </p>
                </div>
              </div>
              <div className="pd-moment-nation-delight">
                <span
                  className="pd-moment-nation-chip pd-moment-nation-chip--meal"
                  data-testid="pd-moment-meal-menu-v1"
                >
                  🍲 {view.delight_meal}
                </span>
                <span className="pd-moment-nation-chip">👗 {view.delight_outfit}</span>
              </div>
              <p className="pd-moment-nation-badge">{view.badge_ko} · preview_only</p>
              <p className="pd-moment-nation-tone">{view.acode_moment_tone}</p>
            </article>
          </>
        )}

        <div className="pd-moment-nation-cta">
          <a className="btn btn-primary" href="#pd-commercial-moment">
            순간 질문하기
          </a>
          <Link className="btn btn-ghost" href={opsHref}>
            내 기지 열기
          </Link>
        </div>
      </div>
    </section>
  );
}
