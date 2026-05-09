import { Fragment } from "react";
import { siteCopy } from "@/content/siteCopy";
import { SiteHeader } from "@/components/SiteHeader";
import { FreeValidationLeadForm } from "@/components/FreeValidationLeadForm";
import { ContactActionLinks } from "@/components/ContactActionLinks";
import { BasicHealthChatCard } from "@/components/BasicHealthChatCard";
import { PaddleCheckoutButton } from "@/components/PaddleCheckoutButton";

export const dynamic = "force-dynamic";

type HomePageProps = {
  searchParams?: {
    preset?: string;
  };
};

const homepagePresetMap = {
  "stripe-linear": "preset-stripe-linear",
  "apple-notion": "preset-apple-notion",
} as const;

export default function HomePage({ searchParams }: HomePageProps) {
  const c = siteCopy;
  const clinicCardFlow = [
    {
      step: "01",
      title: "내원 후 기본 정보 입력",
      body: "증상·생활패턴·문진 정보를 AI 보조 입력폼에 빠르게 정리합니다.",
    },
    {
      step: "02",
      title: "AI가 상담 포인트 정리",
      body: "위험 신호와 확인 질문을 요약해 한의사 진찰 전 체크리스트를 만듭니다.",
    },
    {
      step: "03",
      title: "한의사 진찰·최종 판단",
      body: "AI는 보조만 수행하고, 진단과 처방은 한의사가 최종 확정합니다.",
    },
    {
      step: "04",
      title: "설명·연결·기록 보조",
      body: "환자 이해를 돕는 요약과 다음 내원/관리 포인트를 쉽게 안내합니다.",
    },
  ] as const;
  const heroCtaLinks = {
    primary: c.links.consumer,
    secondary: c.links.clinician,
    tertiary: c.links.contact,
    quaternary: c.links.reception,
  } as const;
  const sectionCtaLinks = {
    publicSolutionPrimary: c.links.consumer,
    publicSolutionSecondary: c.links.contact,
  } as const;

  const presetKey = searchParams?.preset;
  const homepagePresetClass =
    presetKey && presetKey in homepagePresetMap
      ? homepagePresetMap[presetKey as keyof typeof homepagePresetMap]
      : "";

  return (
    <div className={homepagePresetClass}>
      <a className="skip" href="#main">
        본문으로 건너뛰기
      </a>
      <SiteHeader nav={c.nav} brand={c.header} links={c.links} />
      <main id="main">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-orb hero-orb-a" aria-hidden="true" />
          <div className="hero-orb hero-orb-b" aria-hidden="true" />
          <div className="hero-grid-overlay" aria-hidden="true" />
          <span className="eyebrow">{c.hero.eyebrow}</span>
          <h1 id="hero-title">{c.hero.title}</h1>
          <p className="hero-lead">{c.hero.subtitle}</p>
          <div className="hero-cta">
            <a className="btn btn-primary" href={heroCtaLinks.primary}>
              {c.hero.cta_primary}
            </a>
            <a className="btn btn-ghost" href={heroCtaLinks.secondary}>
              {c.hero.cta_secondary}
            </a>
            <a className="btn btn-ghost" href={heroCtaLinks.tertiary}>
              {c.hero.cta_tertiary}
            </a>
            <a className="btn btn-ghost" href={heroCtaLinks.quaternary}>
              {c.hero.cta_quaternary}
            </a>
          </div>
          <div className="hero-role-cta">
            {c.hero.role_cards.map((card) => (
              <article key={card.title} className="card card-lift">
                <h3>{card.title}</h3>
                <p>{card.body}</p>
                <a className={`btn ${card.variant === "primary" ? "btn-primary" : "btn-ghost"}`} href={card.href}>
                  {card.cta}
                </a>
              </article>
            ))}
          </div>
          <div className="hero-proof" role="list" aria-label="핵심 가치">
            <span role="listitem">근거 출처 매핑</span>
            <span role="listitem">의료진 최종판단 고정</span>
            <span role="listitem">일반인 무료 사전 리포트</span>
          </div>
          <div
            className="section-cta hub-cross-links"
            style={{
              marginTop: "1rem",
              display: "flex",
              flexWrap: "wrap",
              gap: "0.5rem",
              alignItems: "center",
            }}
            aria-label="MKM 관련 도메인 안내"
          >
            {(
              ["showroom_jemaai", "premium_mkmlife", "b2b_acodeai"] as const
            ).map((key) => {
              const link = c.hub_links[key];
              return (
                <a
                  key={key}
                  className="btn btn-ghost"
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={link.sublabel}
                >
                  {link.label}
                </a>
              );
            })}
          </div>
        </section>

        <section id="feature-triad" className="feature-triad" aria-labelledby="feature-triad-heading">
          <h2 id="feature-triad-heading" className="sr-only">
            핵심 역량
          </h2>
          <div className="feature-triad-grid">
            {c.feature_triad.cards.map((card) => (
              <article
                key={card.variant}
                className={`feature-triad-card feature-triad-card--${card.variant}`}
              >
                <div className="feature-triad-icon" aria-hidden="true">
                  {card.variant === "copilot" ? (
                    <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
                      <path
                        d="M24 6 38 12v14c0 10-8 18-14 20-6-2-14-10-14-20V12L24 6Z"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinejoin="round"
                      />
                      <path d="M18 24 22 28 31 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                  ) : null}
                  {card.variant === "heritage" ? (
                    <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
                      <circle cx="24" cy="24" r="16" stroke="currentColor" strokeWidth="2" />
                      <path d="M24 14v10l7 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      <path
                        d="M34 34c-3-5-8-8-14-8"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                  ) : null}
                  {card.variant === "sovereign" ? (
                    <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
                      <path
                        d="M14 22c2-8 8-12 10-12s8 4 10 12c1 6-2 14-10 18-8-4-11-12-10-18Z"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinejoin="round"
                      />
                      <path d="M22 26h6M22 30h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                  ) : null}
                </div>
                <h3 className="feature-triad-title">{card.title}</h3>
                <p className="feature-triad-subtitle">{card.subtitle}</p>
                <p className="feature-triad-body">{card.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="quick-start" aria-labelledby="quick-start-title">
          <h2 id="quick-start-title">일반인 홍보·상담 안내와 한의사 진료보조를 분리 운영합니다</h2>
          <p className="section-lead">
            홈페이지에서는 일반인에게 간단 건강상담을 제공하고, 상세 문진은 카카오 설문으로 수집해 한의사 화면에 구조화 전달합니다.
          </p>
          <div className="grid-3">
            <article className="card">
              <h3>1차 상담 (홈페이지)</h3>
              <p>주요 불편 부위·통증·수면/소화 상태를 짧게 입력해 사전 안내를 받습니다.</p>
            </article>
            <article className="card">
              <h3>2차 문진 (카카오 설문)</h3>
              <p>기본 환자 정보, 건강 정보, 체질 판단 최소 문항을 빠르게 완료합니다.</p>
            </article>
            <article className="card">
              <h3>3차 진료 (한의사 최종 판단)</h3>
              <p>SOAP 초안은 AI가 보조하고, 진단·처방·차트 확정은 한의사가 수행합니다.</p>
            </article>
          </div>
          <div className="section-cta">
            <a className="btn btn-primary" href="/consumer?panel=survey#patient-intake">
              카카오 설문 시작하기
            </a>
            <a className="btn btn-ghost" href="/consumer">
              간단 건강상담 먼저 해보기
            </a>
          </div>
        </section>

        <BasicHealthChatCard />

        <section id="brand-motion" aria-labelledby="brand-motion-title">
          <div className="brand-motion-grid">
            <article className="brand-motion-copy">
              <p className="premium-label">{c.concept_block.label}</p>
              <h2 id="brand-motion-title">{c.concept_block.title}</h2>
              <p className="section-lead">
                {c.concept_block.lead}
              </p>
              <div className="hero-proof" role="list" aria-label="브랜드 모션 특징">
                {c.concept_block.proof_items.map((item) => (
                  <span key={item} role="listitem">{item}</span>
                ))}
              </div>
            </article>
            <div className="brand-motion-stage card-lift" aria-hidden="true">
              <div className="brand-motion-canvas" />
              <div className="brand-motion-beam brand-motion-beam-a" />
              <div className="brand-motion-beam brand-motion-beam-b" />
              <div className="brand-motion-grain" />
              <div className="brand-motion-tint" />
              <div className="brand-motion-card-news">
                {clinicCardFlow.map((item) => (
                  <article key={item.step} className="brand-flow-card">
                    <p className="brand-flow-step">STEP {item.step}</p>
                    <h3>{item.title}</h3>
                    <p>{item.body}</p>
                  </article>
                ))}
              </div>
              <div className="brand-motion-label">{c.concept_block.stage_label}</div>
            </div>
          </div>
        </section>

        <section id="trust" aria-label="신뢰 지표">
          <div className="trust-strip" role="list">
            {c.trust.items.map((item) => (
              <article key={item.label} className="trust-item" role="listitem">
                <p>{item.label}</p>
                <strong>{item.value}</strong>
              </article>
            ))}
          </div>
          <p className="trust-note" role="note">
            {c.trust.note}
          </p>
        </section>

        <section id="why-mkm-ai" aria-labelledby="why-mkm-ai-title">
          <h2 id="why-mkm-ai-title">Why MKM AI?</h2>
          <p className="section-lead">
            범용 AI의 구조적 과신 리스크를 그대로 트레이딩에 연결하지 않고, 교차검증과 방어 거버넌스를 통해
            위험 노출을 통제합니다.
          </p>
          <div className="grid-3">
            <article className="card">
              <h3>구조적 과신 리스크</h3>
              <p>
                단일 모델은 불확실성이 큰 구간에서도 답을 강제 생성할 수 있습니다. MKM은 이 구간을 확정 신호가 아닌
                경고/관망 구간으로 분리합니다.
              </p>
            </article>
            <article className="card">
              <h3>4AI 교차검증 + 보수 Veto</h3>
              <p>
                다중 엔진의 교차검증 신호를 정량화하고, 확신이 약한 국면에서는 보수 정책이 <code>HOLD_SAFE</code>를 우선
                선언하도록 설계했습니다.
              </p>
            </article>
            <article className="card">
              <h3>Action+Alert 거버넌스</h3>
              <p>
                Regime transition risk signal은 임계치/히스테리시스/쿨다운 정책으로 제어하며, 조건 충족 시
                <code>EXPOSURE_CONTROL</code>와 경보를 함께 실행합니다.
              </p>
            </article>
          </div>
          <p className="trust-note" role="note">
            본 시스템은 수익 보장을 주장하지 않으며, Track C에서는 risk-warning 및 exposure control 목적의 운영 신호를
            제공합니다.
          </p>
        </section>

        <section id="public-solution" aria-labelledby="public-solution-title">
          <h2 id="public-solution-title">{c.public_solution.title}</h2>
          <p className="section-lead">{c.public_solution.section_lead}</p>
          <div className="grid-3">
            {c.public_solution.cards.map((item) => (
              <article key={item.title} className="card">
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
          <div className="section-cta">
            <a className="btn btn-primary" href={sectionCtaLinks.publicSolutionPrimary}>
              {c.public_solution.cta_primary}
            </a>
            <a className="btn btn-ghost" href={sectionCtaLinks.publicSolutionSecondary}>
              {c.public_solution.cta_secondary}
            </a>
          </div>
        </section>

        <section id="about" aria-labelledby="about-title">
          <h2 id="about-title">{c.about.title}</h2>
          <p className="section-lead">{c.about.section_lead}</p>
          <div className="grid-3">
            {c.value_props.map((vp) => (
              <article key={vp.title} className="card">
                <h3>{vp.title}</h3>
                <p>{vp.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="safety" aria-labelledby="safety-title">
          <h2 id="safety-title">{c.safety.title}</h2>
          <div className="notice-box">
            <ul>
              {c.safety.items.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        </section>

        <section id="workflow" aria-labelledby="flow-title">
          <h2 id="flow-title">{c.workflow.title}</h2>
          <p className="section-lead">{c.workflow.section_lead}</p>
          <div className="steps" role="list">
            {c.workflow.steps.map((step, i) => (
              <Fragment key={step}>
                {i > 0 ? (
                  <span className="arrow" aria-hidden="true">
                    →
                  </span>
                ) : null}
                <span role="listitem">{step}</span>
              </Fragment>
            ))}
          </div>
        </section>

        <section id="clinic-o2o" aria-labelledby="clinic-o2o-title">
          <h2 id="clinic-o2o-title">{c.clinic_o2o.title}</h2>
          <p className="section-lead">{c.clinic_o2o.section_lead}</p>
          <div className="grid-3">
            {c.clinic_o2o.cards.map((card) => (
              <article key={card.title} className="card">
                <h3>{card.title}</h3>
                <p>{card.body}</p>
              </article>
            ))}
          </div>
          <div className="section-cta">
            {c.clinic_o2o.ctas.map((cta) => (
              <a key={cta.label} className={`btn ${cta.variant === "primary" ? "btn-primary" : "btn-ghost"}`} href={cta.href}>
                {cta.label}
              </a>
            ))}
          </div>
        </section>

        <section id="premium-story" aria-labelledby="premium-story-title">
          <h2 id="premium-story-title">{c.landing_flow.title}</h2>
          <p className="section-lead">{c.landing_flow.lead}</p>
          <div className="premium-grid">
            {c.landing_flow.cards.map((item) => (
              <article key={item.title} className="premium-panel card-lift">
                <p className="premium-label">{item.label}</p>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
          <div className="section-cta">
            <a className="btn btn-primary" href={c.links.consumer}>
              {c.landing_flow.cta_primary}
            </a>
            <a className="btn btn-ghost" href={c.links.clinician}>
              {c.landing_flow.cta_secondary}
            </a>
          </div>
        </section>

        <section id="contact" aria-labelledby="contact-title">
          <h2 id="contact-title">{c.contact.title}</h2>
          <p className="section-lead">{c.contact.section_lead}</p>
          <div className="section-cta" style={{ marginBottom: "0.75rem" }}>
            <PaddleCheckoutButton />
          </div>
          <ContactActionLinks email={c.footer.email} label={c.contact.email_label} />
          <FreeValidationLeadForm />
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand">{c.footer.company_line}</div>
          <div className="footer-meta">
            <p>주소: {c.footer.address}</p>
            <p>사업자등록번호: {c.footer.biz_reg}</p>
          </div>
          <div className="footer-legal">{c.footer.rights}</div>
        </div>
      </footer>
    </div>
  );
}
