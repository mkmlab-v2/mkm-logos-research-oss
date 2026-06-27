"use client";

import { Suspense } from "react";

import { MyeongniResearchStudioClient } from "@/components/myeongni-research/MyeongniResearchStudioClient";

export function MyeongniResearchStudioPageBody() {
  return (
    <div className="myeongni-research-page myeongni-research-studio-theme" data-myeongni-studio-shell="1">
      <a className="skip" href="#main">
        본문으로 건너뛰기
      </a>
      <header className="mn-studio-header">
        <div className="mn-studio-header-inner">
          <a className="mn-studio-brand" href="/myeongni-research/studio">
            <span className="mn-studio-brand-title">명리 Studio</span>
            <small>MKM B-track · 중기 방향 [HYPO]</small>
          </a>
          <nav className="mn-studio-nav" aria-label="Myeongni research">
            <a className="mn-studio-nav-muted" href="/hub/myeongni">
              Hub · 명리
            </a>
            <a className="mn-studio-nav-muted" href="/logos-research/studio">
              Logos Studio
            </a>
            <a href="https://jema-ai.com">jema-ai.com</a>
          </nav>
        </div>
      </header>
      <main id="main" className="mn-studio-main">
        <section className="mn-studio-hero">
          <h1>명리 경로 마인드맵</h1>
          <p className="mn-studio-hero-lead">질의 → 四柱 · 대운/세운 · 십성/오행 가지 · research_only</p>
        </section>
        <Suspense fallback={<p className="mn-studio-loading">스튜디오 로딩 중…</p>}>
          <MyeongniResearchStudioClient />
        </Suspense>
      </main>
    </div>
  );
}
