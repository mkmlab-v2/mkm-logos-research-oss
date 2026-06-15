"use client";

import Link from "next/link";
import { personadiaryCopy } from "@/content/personadiaryCopy";
import { personadiaryPublicPath } from "@/lib/personadiaryMobileOpsV1";
import { PersonadiaryDailyGuideCards } from "./PersonadiaryDailyGuideCards";
import { PersonadiaryReflectTeaser } from "./PersonadiaryReflectTeaser";
import { PersonadiaryRitualDraw } from "./PersonadiaryRitualDraw";
import { PersonadiaryDailyGuideProvider } from "./usePersonadiaryDailyGuide";

const HOME_BRIDGE_ROWS = [
  {
    label: "4레인",
    value: "몸·마음·일·쉼 — 한 탭으로 전환",
  },
  {
    label: "Pull 가이드",
    value: "푸시 없음 · 원할 때만 인출",
  },
  {
    label: "로컬 일기",
    value: "IndexedDB만 · 서버 업로드 없음",
  },
  {
    label: "격벽",
    value: "예언·적중·% 단정 없음 · preview_only",
  },
] as const;

export function PersonadiaryPremiumHome() {
  const opsHref = personadiaryPublicPath("/ops");

  return (
    <>
      <section className="pd-home-bridge-hero" aria-labelledby="personadiary-title">
        <div className="pd-premium-section-inner">
          <span className="pd-premium-eyebrow">Persona Diary · Pull-first · preview</span>
          <h1 id="personadiary-title">내 기지</h1>
          <p className="pd-home-bridge-lead">
            비예측형 인지 방화벽 — 주의력은 Pull로만 회수합니다.
          </p>
          <p className="pd-home-bridge-sub">
            4레인 · 주간 5 · 지금 1타 · 로컬 일기 · SEND_GATE: HOLD
          </p>
          <div className="pd-premium-cta pd-home-bridge-cta-row">
            <Link className="btn btn-primary pd-home-bridge-cta-primary" href={opsHref}>
              내 기지 열기
            </Link>
            <a className="btn btn-ghost" href={personadiaryCopy.links.waitlist}>
              사전 알림
            </a>
            <Link className="btn btn-ghost" href={personadiaryCopy.links.demo}>
              콘셉트 데모
            </Link>
          </div>
        </div>
      </section>

      <section className="pd-home-bridge-features" aria-labelledby="pd-bridge-features-title">
        <div className="pd-premium-section-inner">
          <p id="pd-bridge-features-title" className="pd-ios-group-label">
            기지에서 하는 일
          </p>
          <div className="pd-ios-inset pd-home-feature-inset">
            {HOME_BRIDGE_ROWS.map((row, index) => (
              <div
                key={row.label}
                className={`pd-ios-row pd-ios-row--static${
                  index < HOME_BRIDGE_ROWS.length - 1 ? " pd-ios-row--divider" : ""
                }`}
              >
                <span className="pd-ios-row-label">{row.label}</span>
                <span className="pd-ios-row-value">{row.value}</span>
              </div>
            ))}
          </div>
          <p className="pd-home-bridge-hint">
            iPhone: Safari에서 열고 <strong>홈 화면에 추가</strong>하면 앱처럼 씁니다.
          </p>
          <Link className="btn btn-primary pd-home-bridge-cta-secondary" href={opsHref}>
            내 기지로 이동
          </Link>
        </div>
      </section>

      <PersonadiaryDailyGuideProvider>
        <PersonadiaryRitualDraw />

        <section
          className="pd-premium-reflect-section pd-home-preview-section"
          aria-labelledby="pd-reflect-home-title"
        >
          <div className="pd-premium-section-inner">
            <h2 id="pd-reflect-home-title">홈 미리보기 · 빛의 구슬</h2>
            <p className="pd-premium-section-lead">
              아래는 체험용 미리보기입니다. 매일 쓰는 기지는{" "}
              <Link href={opsHref}>내 기지(/ops)</Link>에서 이어집니다.
            </p>
            <div className="pd-premium-reflect-grid">
              <div className="pd-glass pd-premium-reflect-panel">
                <PersonadiaryReflectTeaser />
                <PersonadiaryDailyGuideCards />
              </div>
              <aside className="pd-glass pd-premium-aside">
                <h3>성찰 셸 (preview)</h3>
                <p>
                  시각·청각 리플렉션만 제공합니다. 영속 저장·결제·임상 연동은 기지 범위와
                  별도입니다.
                </p>
                <p className="pd-premium-aside-muted">
                  Logos·렌즈는 <span className="pd-ops-hypo-tag">[NON_GATING]</span> · 의료·투자
                  조언 아님
                </p>
              </aside>
            </div>
          </div>
        </section>
      </PersonadiaryDailyGuideProvider>

      <section className="pd-premium-pillars pd-home-pillars" aria-labelledby="pd-pillars-title">
        <div className="pd-premium-section-inner">
          <h2 id="pd-pillars-title">프리뷰 검증 축</h2>
          <p className="pd-premium-section-lead">
            유용함 ≠ 예측 적중. B-track 성찰·리듬 보조만 — Track A·실매매 합선 없음.
          </p>
          <div className="pd-pillar-grid">
            <article className="pd-glass pd-pillar-card">
              <span className="pd-pillar-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2M12 20v2M2 12h2M20 12h2" />
                </svg>
              </span>
              <h3>한 줄 성찰</h3>
              <p>매일 짧게 정리하는 로컬 일기·체크포인트 (예언·적중 아님).</p>
            </article>
            <article className="pd-glass pd-pillar-card">
              <span className="pd-pillar-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 3c-4 0-7 2.5-7 6 0 5 7 12 7 12s7-7 7-12c0-3.5-3-6-7-6z" />
                </svg>
              </span>
              <h3>Pull 가이드</h3>
              <p>오늘의 흐름·질문거리 — 푸시 없이 버튼으로만 인출합니다.</p>
            </article>
            <article className="pd-glass pd-pillar-card">
              <span className="pd-pillar-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="4" y="4" width="16" height="16" rx="3" />
                  <path d="M8 12h8M12 8v8" />
                </svg>
              </span>
              <h3>레인 1탭</h3>
              <p>
                OS 스크린타임 설정 대신 인지 레인 전환 — v0.9는 차단 stub, Phase 2에서 API 연동
                [HYPO].
              </p>
            </article>
          </div>
        </div>
      </section>
    </>
  );
}
