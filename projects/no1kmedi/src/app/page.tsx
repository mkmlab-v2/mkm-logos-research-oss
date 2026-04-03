import { Fragment } from "react";
import { siteCopy } from "@/content/siteCopy";
import { SiteHeader } from "@/components/SiteHeader";

export default function HomePage() {
  const c = siteCopy;

  return (
    <>
      <a className="skip" href="#main">
        본문으로 건너뛰기
      </a>
      <SiteHeader nav={c.nav} />
      <main id="main">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <span className="eyebrow">{c.hero.eyebrow}</span>
          <h1 id="hero-title">{c.hero.title}</h1>
          <p className="hero-lead">{c.hero.subtitle}</p>
          <div className="hero-cta">
            <a className="btn btn-primary" href="#contact">
              {c.hero.cta_primary}
            </a>
            <a className="btn btn-ghost" href="#about">
              {c.hero.cta_secondary}
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

        <section id="contact" aria-labelledby="contact-title">
          <h2 id="contact-title">{c.contact.title}</h2>
          <p className="section-lead">{c.contact.section_lead}</p>
          <p>
            {c.contact.email_label}: <a href={`mailto:${c.footer.email}`}>{c.footer.email}</a>
          </p>
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
    </>
  );
}
