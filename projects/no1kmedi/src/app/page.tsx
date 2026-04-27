import { Fragment } from "react";
import { siteCopy } from "@/content/siteCopy";
import { SiteHeader } from "@/components/SiteHeader";
import { FreeValidationLeadForm } from "@/components/FreeValidationLeadForm";
import { ContactActionLinks } from "@/components/ContactActionLinks";

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
  const presetKey = searchParams?.preset?.toLowerCase();
  const homepagePresetClass =
    (presetKey && homepagePresetMap[presetKey as keyof typeof homepagePresetMap]) ??
    "preset-apple-notion";
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
        </section>

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
