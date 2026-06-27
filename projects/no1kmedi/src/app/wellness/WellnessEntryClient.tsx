"use client";

import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { HubDomainCrossLinks, HUB_FOOTER_KEYS } from "@/components/HubDomainCrossLinks";
import type { PatientWellnessCard, PatientWellnessEntryCopy, SiteCopy } from "@/content/siteCopy";

function CopyBlock({ id, label, text }: { id: string; label: string; text: string }) {
  return (
    <div className="wellness-kakao-block">
      <div className="wellness-kakao-block-head">
        <h3>{label}</h3>
        <button
          type="button"
          className="btn btn-soft btn-sm"
          onClick={() => {
            void navigator.clipboard.writeText(text).then(() => {
              const el = document.getElementById(id);
              if (el) el.dataset.copied = "1";
              window.setTimeout(() => {
                if (el) delete el.dataset.copied;
              }, 1800);
            });
          }}
        >
          복사
        </button>
      </div>
      <pre id={id} className="wellness-kakao-pre">
        {text}
      </pre>
      <p className="wellness-kakao-hint">채널 관리자용 · 법무 검토 전 배포 금지 (SEND_GATE: HOLD)</p>
    </div>
  );
}

function WellnessCard({ card }: { card: PatientWellnessCard }) {
  if (card.variant === "rhythm") {
    return (
      <article className={`wellness-card wellness-card--${card.variant}`}>
        <h3>{card.title}</h3>
        <p>{card.body}</p>
        <div className="wellness-card-actions">
          <a
            className="btn btn-primary"
            href={card.cta_primary.href}
            {...(card.cta_primary.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
          >
            {card.cta_primary.label}
          </a>
          <Link className="btn btn-ghost" href={card.cta_secondary.href}>
            {card.cta_secondary.label}
          </Link>
          <Link className="btn btn-ghost wellness-card-ghost" href={card.cta_ghost.href}>
            {card.cta_ghost.label}
          </Link>
        </div>
      </article>
    );
  }

  return (
    <article className={`wellness-card wellness-card--${card.variant}`}>
      <h3>{card.title}</h3>
      <ul className="wellness-card-list">
        {card.items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
  );
}

type Props = {
  copy: PatientWellnessEntryCopy;
  site: Pick<SiteCopy, "header" | "nav" | "links" | "hub_links" | "footer">;
};

export function WellnessEntryClient({ copy, site }: Props) {
  return (
    <>
      <a className="skip" href="#wellness-main">
        본문으로 건너뛰기
      </a>
      <SiteHeader nav={site.nav} brand={site.header} links={site.links} />
      <main id="wellness-main" className="wellness-entry-page">
        <section className="wellness-entry-hero mkm-section" aria-labelledby="wellness-hero-title">
          <div className="wellness-entry-inner">
            <span className="wellness-entry-badge">{copy.badge_non_medical}</span>
            <p className="wellness-entry-eyebrow">{copy.hero.eyebrow}</p>
            <h1 id="wellness-hero-title">{copy.hero.title}</h1>
            <p className="wellness-entry-lead">{copy.hero.lead}</p>
            <p className="wellness-entry-hold" role="note">
              SEND_GATE: HOLD · ready_for_external_send: false · 법무·의료광고 검토 전 대외·카톡 무단 배포 금지
            </p>
          </div>
        </section>

        <section className="wellness-entry-cards mkm-section" aria-labelledby="wellness-cards-title">
          <div className="wellness-entry-inner">
            <h2 id="wellness-cards-title" className="visually-hidden">
              제공 범위 안내
            </h2>
            <div className="wellness-card-grid">
              {copy.cards.map((card) => (
                <WellnessCard key={card.title} card={card} />
              ))}
            </div>
          </div>
        </section>

        <section className="wellness-entry-kakao mkm-section" aria-labelledby="wellness-kakao-title">
          <div className="wellness-entry-inner">
            <h2 id="wellness-kakao-title">카카오 채널 · 정형 카피 (1-way)</h2>
            <p className="section-lead">
              무한 AI 상담이 아닌 고정 안내 블록만 사용합니다. 아래 텍스트를 복사해 채널 관리자 도구에 붙여 넣으세요.
            </p>
            <CopyBlock id="wellness-kakao-intro" label="인트로 블록" text={copy.kakao_blocks.intro} />
            <CopyBlock id="wellness-kakao-links" label="링크 블록" text={copy.kakao_blocks.links} />
          </div>
        </section>

        <section className="wellness-entry-disclaimer mkm-section" aria-labelledby="wellness-disclaimer-title">
          <div className="wellness-entry-inner">
            <div className="wellness-disclaimer-panel">
              <h2 id="wellness-disclaimer-title">{copy.disclaimer.title}</h2>
              <p>{copy.disclaimer.body}</p>
              <ul>
                {copy.disclaimer.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="wellness-disclaimer-ssot">
                SSOT: docs/final/artifacts/patient_wellness_entry_copy_v1_latest.md
              </p>
            </div>
            <HubDomainCrossLinks hubLinks={site.hub_links} keys={HUB_FOOTER_KEYS} className="hub-cross-links footer-hub-links" />
          </div>
        </section>
      </main>
      <footer className="site-footer wellness-entry-footer">
        <div className="footer-inner">
          <p>{site.footer.company_line}</p>
          <p className="footer-muted">{site.footer.brand_subline}</p>
          <p className="footer-muted">{site.footer.rights}</p>
        </div>
      </footer>
    </>
  );
}
