import type { Metadata } from "next";
import { siteCopy } from "@/content/siteCopy";
import { DEFAULT_HOMEPAGE_PRESET, homepagePresetClassMap } from "@/lib/homepagePreset";

function requireEnterprise() {
  const e = siteCopy.enterprise;
  if (!e) {
    throw new Error("public-copy.json: enterprise block is required for /enterprise");
  }
  return e;
}

export function generateMetadata(): Metadata {
  const ent = requireEnterprise();
  return {
    title: ent.seo.title,
    description: ent.seo.description,
  };
}

export default function EnterprisePage() {
  const c = siteCopy;
  const e = requireEnterprise();
  const presetClass = homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];
  const showroom = c.hub_links.showroom_jemaai;
  const qaStudio = c.hub_links.showroom_meaning_qa_v2 ?? showroom;
  const topologyRadar = c.hub_links.showroom_topology_radar;
  const meaningGraph = c.hub_links.showroom_meaning_graph;
  const api = c.hub_links.b2b_acodeai;

  return (
    <div className={`${presetClass} enterprise-page`}>
      <a className="skip" href="#main">
        본문으로 건너뛰기
      </a>
      <header className="site-header enterprise-header">
        <div className="header-inner">
          <a className="brand" href="/enterprise">
            {c.header.brand_name} <span>{e.nav.brand_tagline}</span>
          </a>
          <nav className="nav-main enterprise-nav" aria-label="기업·파트너">
            <a href="/">{e.nav.back_home}</a>
            <a href="#pillars">{e.nav.pillars}</a>
            <a href="#proof">{e.nav.proof}</a>
            <a href="#research">{e.nav.research}</a>
            <a href="#contact">{e.nav.contact}</a>
          </nav>
        </div>
      </header>

      <main id="main">
        <section className="hero enterprise-hero" aria-labelledby="enterprise-hero-title">
          <div className="enterprise-hero-noise" aria-hidden="true" />
          <div className="hero-orb hero-orb-a" aria-hidden="true" />
          <div className="hero-orb hero-orb-b" aria-hidden="true" />
          <div className="hero-grid-overlay" aria-hidden="true" />
          <span className="eyebrow enterprise-eyebrow">{e.hero.eyebrow}</span>
          <h1 id="enterprise-hero-title">{e.hero.title}</h1>
          <p className="hero-lead">{e.hero.subtitle}</p>
          <div className="hero-cta">
            <a
              className="btn btn-primary enterprise-btn-primary"
              href={qaStudio.href}
              target="_blank"
              rel="noopener noreferrer"
              title={qaStudio.sublabel}
            >
              {e.hero.cta_primary}
            </a>
            <a
              className="btn btn-ghost enterprise-btn-ghost"
              href={api.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              {e.hero.cta_secondary}
            </a>
          </div>
        </section>

        <section className="enterprise-principles" aria-label="핵심 원칙">
          <ul className="enterprise-principles-grid">
            {e.principles.map((item) => (
              <li key={item.title} className="enterprise-principle-chip">
                <strong>{item.title}</strong>
                <span>{item.body}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="enterprise-composition" aria-labelledby="composition-title">
          <h2 id="composition-title" className="enterprise-composition-title">
            {e.composition.title}
          </h2>
          <ol className="enterprise-composition-track">
            {e.composition.items.map((row) => (
              <li key={row.label} className="enterprise-composition-row">
                <span className="enterprise-composition-share">{row.share}</span>
                <div>
                  <strong>{row.label}</strong>
                  <p>{row.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section id="pillars" className="enterprise-pillar-primary" aria-labelledby="pillars-title">
          <p className="enterprise-section-label">{e.pillars.section_label}</p>
          <h2 id="pillars-title">{e.pillars.title}</h2>
          <p className="section-lead">{e.pillars.lead}</p>
          <div className="enterprise-pillar-grid">
            {e.pillars.cards.map((card, index) => (
              <article key={card.title} className="enterprise-pillar-card">
                <span className="enterprise-pillar-index" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3>{card.title}</h3>
                <p>{card.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="enterprise-pillar-secondary" aria-labelledby="breadth-title">
          <p className="enterprise-section-label">{e.breadth.section_label}</p>
          <h2 id="breadth-title">{e.breadth.title}</h2>
          <p className="section-lead enterprise-breadth-body">{e.breadth.body}</p>
        </section>

        <section className="enterprise-applications-wrap" aria-labelledby="applications-title">
          <h2 id="applications-title">{e.applications.title}</h2>
          <p className="section-lead">{e.applications.lead}</p>
          <div className="enterprise-applications-grid">
            {e.applications.items.map((item) => (
              <article key={item.title} className="enterprise-app-card">
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="proof" className="enterprise-proof" aria-labelledby="proof-title">
          <h2 id="proof-title">{e.proof.title}</h2>
          <p className="section-lead">{e.proof.lead}</p>
          <div className="enterprise-proof-grid">
            <a
              className="enterprise-proof-card enterprise-proof-card--primary"
              href={qaStudio.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="enterprise-proof-card-label">B2B 데모</span>
              <strong>{qaStudio.label}</strong>
              <p>{qaStudio.sublabel}</p>
              <span className="enterprise-proof-card-arrow" aria-hidden="true">
                →
              </span>
            </a>
            {topologyRadar ? (
              <a
                className="enterprise-proof-card"
                href={topologyRadar.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="enterprise-proof-card-label">레이더</span>
                <strong>{topologyRadar.label}</strong>
                <p>{topologyRadar.sublabel}</p>
                <span className="enterprise-proof-card-arrow" aria-hidden="true">
                  →
                </span>
              </a>
            ) : null}
            {meaningGraph ? (
              <a
                className="enterprise-proof-card"
                href={meaningGraph.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="enterprise-proof-card-label">그래프</span>
                <strong>{meaningGraph.label}</strong>
                <p>{meaningGraph.sublabel}</p>
                <span className="enterprise-proof-card-arrow" aria-hidden="true">
                  →
                </span>
              </a>
            ) : null}
            <a
              className="enterprise-proof-card"
              href={showroom.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="enterprise-proof-card-label">보드</span>
              <strong>{showroom.label}</strong>
              <p>{showroom.sublabel}</p>
              <span className="enterprise-proof-card-arrow" aria-hidden="true">
                →
              </span>
            </a>
            <a
              className="enterprise-proof-card"
              href={api.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="enterprise-proof-card-label">개발</span>
              <strong>{api.label}</strong>
              <p>{api.sublabel}</p>
              <span className="enterprise-proof-card-arrow" aria-hidden="true">
                →
              </span>
            </a>
            <a className="enterprise-proof-card enterprise-proof-card--internal" href="/">
              <span className="enterprise-proof-card-label">허브</span>
              <strong>{e.nav.back_home}</strong>
              <p>임상·소비자 제품 안내</p>
              <span className="enterprise-proof-card-arrow" aria-hidden="true">
                →
              </span>
            </a>
          </div>
        </section>

        <section id="research" className="enterprise-research" aria-labelledby="research-title">
          <p className="enterprise-section-label">{e.research.section_label}</p>
          <h2 id="research-title">{e.research.title}</h2>
          <p className="section-lead">{e.research.body}</p>
          <a className="btn btn-ghost enterprise-research-link" href={e.research.link_href}>
            {e.research.link_label}
          </a>
        </section>

        <section id="contact" className="enterprise-disclaimer" aria-labelledby="disclaimer-title">
          <h2 id="disclaimer-title">{e.disclaimer.title}</h2>
          <ul>
            {e.disclaimer.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="enterprise-contact-hint">
            {e.contact.label}:{" "}
            <a href={`mailto:${e.contact.email}`}>{e.contact.email}</a>
          </p>
        </section>
      </main>

      <footer className="site-footer enterprise-footer">
        <p>
          <a href="/">jema-ai.com</a> · <a href="/company">회사 소개</a> ·{" "}
          <a href={`mailto:${c.footer.email}`}>{c.footer.email}</a>
        </p>
        <p className="footer-muted">
          {c.footer.company_line} · {c.footer.brand_subline}
        </p>
        <p className="footer-muted">{c.footer.rights}</p>
      </footer>
    </div>
  );
}
