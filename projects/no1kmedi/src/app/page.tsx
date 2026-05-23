import { Fragment, type ReactNode } from "react";
import { resolveHomepagePresetClass } from "@/lib/homepagePreset";
import { siteCopy } from "@/content/siteCopy";
import { SiteHeader } from "@/components/SiteHeader";
import { FreeValidationLeadForm } from "@/components/FreeValidationLeadForm";
import { ContactActionLinks } from "@/components/ContactActionLinks";
import { BasicHealthChatCard } from "@/components/BasicHealthChatCard";
import { HomepageAppEntry } from "@/components/HomepageAppEntry";
import { FieldLensGovernanceFlow } from "@/components/FieldLensGovernanceFlow";
import { HomeHeroSection } from "@/components/HomeHeroSection";
import { PaddleCheckoutButton } from "@/components/PaddleCheckoutButton";

export const dynamic = "force-dynamic";

function renderBodyWithCodeTerms(body: string, codeTerms?: string[]): ReactNode {
  if (!codeTerms?.length) return body;
  const pattern = new RegExp(`(${codeTerms.join("|")})`, "g");
  return body.split(pattern).map((part, idx) =>
    codeTerms.includes(part) ? <code key={`code-${idx}`}>{part}</code> : <Fragment key={`t-${idx}`}>{part}</Fragment>,
  );
}

type HomePageProps = {
  searchParams?: {
    preset?: string;
  };
};

export default function HomePage({ searchParams }: HomePageProps) {
  const c = siteCopy;
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

  const homepagePresetClass = resolveHomepagePresetClass(searchParams?.preset);

  return (
    <div className={homepagePresetClass}>
      <a className="skip" href="#main">
        {c.homepage_a11y.skip_to_main}
      </a>
      <SiteHeader nav={c.nav} brand={c.header} links={c.links} />
      <main id="main">
        <HomeHeroSection hero={c.hero} hubLinks={c.hub_links} ctaLinks={heroCtaLinks} />

        <HomepageAppEntry copy={c.app_entry} />

        <section id="feature-triad" className="feature-triad" aria-labelledby="feature-triad-heading">
          <h2 id="feature-triad-heading" className="sr-only">
            {c.homepage_a11y.feature_triad_heading}
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
          <h2 id="quick-start-title">{c.quick_start.title}</h2>
          <p className="section-lead">{c.quick_start.section_lead}</p>
          <div className="grid-3">
            {c.quick_start.cards.map((item) => (
              <article key={item.title} className="card">
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
          <div className="section-cta">
            {c.quick_start.ctas.map((cta) => (
              <a
                key={cta.label}
                className={`btn ${cta.variant === "primary" ? "btn-primary" : "btn-ghost"}`}
                href={cta.href === "/clinician" ? c.links.clinician : cta.href}
              >
                {cta.label}
              </a>
            ))}
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
              <div className="hero-proof" role="list" aria-label={c.homepage_a11y.brand_motion_proof_label}>
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
                {c.home_clinic_flow.steps.map((item) => (
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

        <section id="trust" aria-label={c.homepage_a11y.trust_section_label}>
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

        <FieldLensGovernanceFlow copy={c.governance_flow} />

        <section id="why-mkm-ai" aria-labelledby="why-mkm-ai-title">
          <h2 id="why-mkm-ai-title">{c.why_mkm_ai.title}</h2>
          <p className="section-lead">{c.why_mkm_ai.section_lead}</p>
          <div className="grid-3">
            {c.why_mkm_ai.cards.map((item) => (
              <article key={item.title} className="card">
                <h3>{item.title}</h3>
                <p>{renderBodyWithCodeTerms(item.body, item.code_terms)}</p>
              </article>
            ))}
          </div>
          <p className="trust-note" role="note">
            {c.why_mkm_ai.disclaimer}
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
          <div className="section-cta section-cta--contact-paddle">
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
            <p>{c.footer.brand_subline}</p>
            <p>
              {c.footer.address_label}: {c.footer.address}
            </p>
            <p>
              {c.footer.biz_reg_label}: {c.footer.biz_reg}
            </p>
          </div>
          <div className="footer-legal">{c.footer.rights}</div>
        </div>
      </footer>
    </div>
  );
}
