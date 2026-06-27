"use client";

import Link from "next/link";
import type { DailyGuidePackage } from "@/lib/personadiaryDailyGuide";
import { personadiaryPublicPath } from "@/lib/personadiaryMobileOpsV1";
import { PersonadiaryCommercialBundleGuard } from "./PersonadiaryCommercialBundleGuard";
import { PersonadiaryDailyGuideCards } from "./PersonadiaryDailyGuideCards";
import { PersonadiaryDailyGuideProvider } from "./usePersonadiaryDailyGuide";
import { PersonadiaryMomentNationHero } from "./PersonadiaryMomentNationHero";
import { PersonadiaryPersonaVisualCard } from "./PersonadiaryPersonaVisualCard";
import { PersonadiaryPlusTeaser } from "./PersonadiaryPlusTeaser";
import { PersonadiaryReflectTeaser } from "./PersonadiaryReflectTeaser";
import { PersonadiaryRitualDraw } from "./PersonadiaryRitualDraw";

const COMMERCIAL_PILLARS = [
  {
    title: "찰나의 나라",
    body: "뉴스·날씨·거시와 지금의 나 — 하루 한 장의 융합 카드.",
  },
  {
    title: "찰나 질문",
    body: "점심·옷·마음·세상 — 순간 답 + 오늘 맞춤 메뉴 힌트 [가설].",
  },
  {
    title: "로컬 기지",
    body: "4레인 일기·북극성 — IndexedDB만, 서버 업로드 없음.",
  },
] as const;

export function PersonadiaryPremiumHome({
  initialPackage = null,
}: {
  initialPackage?: DailyGuidePackage | null;
}) {
  const opsHref = personadiaryPublicPath("/ops");

  return (
    <PersonadiaryDailyGuideProvider packageOverride={initialPackage}>
      <PersonadiaryCommercialBundleGuard />
      <span className="pd-commercial-home-ssot" hidden aria-hidden>
        pd-commercial-home-v1
      </span>

      <PersonadiaryMomentNationHero />

      <section
        className="pd-commercial-moment-section"
        aria-labelledby="pd-commercial-moment-title"
        id="pd-commercial-moment"
      >
        <div className="pd-premium-section-inner">
          <h2 id="pd-commercial-moment-title">찰나 질문</h2>
          <p className="pd-commercial-moment-lead">
            오늘 이 순간만의 답 — 의료·투자·운세 단정 없이, 가볍고 귀여운 가이드
          </p>
          <div className="pd-glass pd-commercial-moment-panel">
            <PersonadiaryReflectTeaser />
          </div>
        </div>
      </section>

      <PersonadiaryPersonaVisualCard />

      <PersonadiaryRitualDraw />

      <PersonadiaryPlusTeaser />

      <section className="pd-commercial-ops-bridge" aria-labelledby="pd-ops-bridge-title">
        <div className="pd-premium-section-inner">
          <h2 id="pd-ops-bridge-title">내 기지 · 매일 쓰는 일기</h2>
          <p className="pd-commercial-ops-lead">
            Pull 가이드 · 4레인 일기 · 주간 목표 — PWA로 홈 화면에 추가해 앱처럼 씁니다.
          </p>
          <Link className="btn btn-primary" href={opsHref}>
            내 기지 열기 (/ops)
          </Link>
        </div>
      </section>

      <section
        className="pd-premium-reflect-section pd-home-guide-section"
        aria-labelledby="pd-guide-home-title"
      >
        <div className="pd-premium-section-inner">
          <h2 id="pd-guide-home-title">오늘의 가이드 카드</h2>
          <p className="pd-premium-section-lead">
            A-Code·라이프 렌즈 — 성찰 보조 입력이며 예언·적중이 아닙니다.
          </p>
          <PersonadiaryDailyGuideCards />
        </div>
      </section>

      <section className="pd-premium-pillars pd-home-pillars" aria-labelledby="pd-pillars-title">
        <div className="pd-premium-section-inner">
          <h2 id="pd-pillars-title">Persona Diary · 상용 프리뷰</h2>
          <p className="pd-premium-section-lead">
            mkmlife·jema-ai·Track A와 API·결제·데이터 합선 없음 · preview_only
          </p>
          <div className="pd-pillar-grid">
            {COMMERCIAL_PILLARS.map((pillar) => (
              <article key={pillar.title} className="pd-glass pd-pillar-card">
                <h3>{pillar.title}</h3>
                <p>{pillar.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </PersonadiaryDailyGuideProvider>
  );
}
