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
  const api = c.hub_links.b2b_acodeai;
  const wttDemo = c.hub_links.wtt_persona_os_demo;
  const compressionRoi = c.hub_links.compression_roi_dashboard;
  const evidencePack = c.hub_links.evidence_pack_v0;

  return (
    <div className={`${presetClass} enterprise-page`}>
      <a className="skip" href="#main">
        {c.homepage_a11y.skip_to_main}
      </a>
      <header className="site-header enterprise-header">
        <div className="header-inner">
          <a className="brand" href="/enterprise">
            {c.header.brand_name} <span>{e.nav.brand_tagline}</span>
          </a>
          <nav className="nav-main enterprise-nav" aria-label={e.nav.main_aria_label}>
            <a href="/">{e.nav.back_home}</a>
            {e.jema_os ? <a href="#jema-os">{e.nav.jema_os ?? e.jema_os.section_label}</a> : null}
            <a href="#pillars">{e.nav.pillars}</a>
            <a href="#wtt-persona-os">Persona OS</a>
            <a href="#compression-roi">Compression</a>
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
              href={showroom.href}
              target="_blank"
              rel="noopener noreferrer"
              title={showroom.sublabel}
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

        {e.jema_os ? (
          <section id="jema-os" className="enterprise-jema-os" aria-labelledby="jema-os-title">
            <p className="enterprise-section-label">{e.jema_os.section_label}</p>
            <h2 id="jema-os-title">{e.jema_os.title}</h2>
            <p className="section-lead">{e.jema_os.lead}</p>
            <ol className="enterprise-jema-os-pipeline" aria-label="Neuro Symbolic Human pipeline">
              {e.jema_os.pipeline.map((step) => (
                <li key={step.stage} className="enterprise-jema-os-pipeline-step">
                  <span className="enterprise-jema-os-stage">{step.stage}</span>
                  <div>
                    <strong>{step.label}</strong>
                    <p>{step.body}</p>
                  </div>
                </li>
              ))}
            </ol>
            <h3 className="enterprise-jema-os-composition-title">{e.jema_os.composition.title}</h3>
            <ol className="enterprise-composition-track enterprise-jema-os-composition">
              {e.jema_os.composition.items.map((row) => (
                <li key={row.label} className="enterprise-composition-row">
                  <span className="enterprise-composition-share">{row.share}</span>
                  <div>
                    <strong>{row.label}</strong>
                    <p>{row.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
            <ul className="enterprise-jema-os-bullets">
              {e.jema_os.bullets.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <div className="enterprise-jema-os-not-claims" role="note">
              <span className="enterprise-jema-os-not-label">주장하지 않음</span>
              <ul>
                {e.jema_os.not_claims.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="enterprise-jema-os-actions">
              <a
                className="btn btn-primary enterprise-btn-primary"
                href={e.jema_os.oss_cta.href}
                target="_blank"
                rel="noopener noreferrer"
                title={e.jema_os.oss_cta.sublabel}
              >
                {e.jema_os.oss_cta.label}
              </a>
            </div>
            <p className="enterprise-jema-os-footnote">{e.jema_os.footnote}</p>
          </section>
        ) : null}

        <section className="enterprise-principles" aria-label={e.nav.principles_aria_label}>
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

        <section id="wtt-persona-os" className="enterprise-wtt" aria-labelledby="wtt-title">
          <p className="enterprise-section-label">{e.wtt_persona_os.section_label}</p>
          <h2 id="wtt-title">{e.wtt_persona_os.title}</h2>
          <p className="section-lead">{e.wtt_persona_os.lead}</p>
          <div className="enterprise-wtt-layout">
            <div className="enterprise-wtt-mock" aria-hidden="true">
              <div className="enterprise-wtt-mock-bar">
                <span className="enterprise-wtt-mock-pill hold">SEND HOLD</span>
                <span className="enterprise-wtt-mock-pill">[HYPO]</span>
              </div>
              <div className="enterprise-wtt-mock-grid">
                <div className="enterprise-wtt-mock-col">
                  <span className="enterprise-wtt-mock-label">시나리오</span>
                  <div className="enterprise-wtt-mock-chip is-active">VIP · 휴먼 요청</div>
                  <div className="enterprise-wtt-mock-chip">환불 · 마스킹</div>
                </div>
                <div className="enterprise-wtt-mock-col enterprise-wtt-mock-col--main">
                  <span className="enterprise-wtt-mock-label">워크스페이스</span>
                  <div className="enterprise-wtt-mock-input">복붙 답변 그만하고 사람 연결해 주세요.</div>
                  <div className="enterprise-wtt-mock-actions">
                    <span className="enterprise-wtt-mock-btn">스캔 + FSM</span>
                  </div>
                </div>
                <div className="enterprise-wtt-mock-col">
                  <span className="enterprise-wtt-mock-label">텔레메트리</span>
                  <div className="enterprise-wtt-mock-gauge">
                    <div className="enterprise-wtt-mock-gauge-fill" style={{ width: "42%" }} />
                  </div>
                  <div className="enterprise-wtt-mock-badges">
                    <span>elevated</span>
                    <span>cum 0.41</span>
                  </div>
                </div>
              </div>
              <p className="enterprise-wtt-mock-caption">{e.wtt_persona_os.mock_caption}</p>
            </div>
            <div className="enterprise-wtt-copy">
              <ul className="enterprise-wtt-bullets">
                {e.wtt_persona_os.bullets.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {wttDemo ? (
                <a
                  className="btn btn-primary enterprise-btn-primary"
                  href={wttDemo.href}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {e.wtt_persona_os.cta_label}
                </a>
              ) : null}
            </div>
          </div>
        </section>

        <section id="compression-roi" className="enterprise-compression-roi" aria-labelledby="compression-roi-title">
          <p className="enterprise-section-label">{e.compression_roi.section_label}</p>
          <h2 id="compression-roi-title">{e.compression_roi.title}</h2>
          <p className="section-lead">{e.compression_roi.lead}</p>
          <div className="enterprise-compression-roi-card">
            <div className="enterprise-compression-roi-metrics" aria-hidden="true">
              <div className="enterprise-compression-roi-metric">
                <span>프록시 절감률</span>
                <strong>~14%</strong>
                <small>pilot measured · not headline</small>
              </div>
              <div className="enterprise-compression-roi-metric">
                <span>Jaccard 프록시</span>
                <strong>~0.85</strong>
                <small>operational post-processor</small>
              </div>
              <div className="enterprise-compression-roi-metric">
                <span>send_gate</span>
                <strong>HOLD</strong>
                <small>counsel + contract</small>
              </div>
            </div>
            <p className="enterprise-compression-roi-note">{e.compression_roi.artifact_note}</p>
            <div className="enterprise-compression-roi-actions">
              {e.compression_roi.apply_href ? (
                <a className="btn btn-primary enterprise-btn-primary" href={e.compression_roi.apply_href}>
                  {e.compression_roi.apply_cta_label ?? "무료 사전 감사 신청"}
                </a>
              ) : null}
              {compressionRoi ? (
                <a className="btn btn-ghost enterprise-btn-ghost" href={compressionRoi.href}>
                  {e.compression_roi.cta_label}
                </a>
              ) : null}
            </div>
          </div>
        </section>

        <section id="proof" className="enterprise-proof" aria-labelledby="proof-title">
          <h2 id="proof-title">{e.proof.title}</h2>
          <p className="section-lead">{e.proof.lead}</p>
          <div className="enterprise-proof-grid">
            <a
              className="enterprise-proof-card enterprise-proof-card--primary"
              href={showroom.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="enterprise-proof-card-label">공개 관측</span>
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
            {wttDemo ? (
              <a
                className="enterprise-proof-card"
                href={wttDemo.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="enterprise-proof-card-label">Persona OS</span>
                <strong>{wttDemo.label}</strong>
                <p>{wttDemo.sublabel}</p>
                <span className="enterprise-proof-card-arrow" aria-hidden="true">
                  →
                </span>
              </a>
            ) : null}
            {compressionRoi ? (
              <a className="enterprise-proof-card" href={compressionRoi.href}>
                <span className="enterprise-proof-card-label">Compression</span>
                <strong>{compressionRoi.label}</strong>
                <p>{compressionRoi.sublabel}</p>
                <span className="enterprise-proof-card-arrow" aria-hidden="true">
                  →
                </span>
              </a>
            ) : null}
            {evidencePack ? (
              <a className="enterprise-proof-card enterprise-proof-card--primary" href={evidencePack.href}>
                <span className="enterprise-proof-card-label">Evidence</span>
                <strong>{evidencePack.label}</strong>
                <p>{evidencePack.sublabel}</p>
                <span className="enterprise-proof-card-arrow" aria-hidden="true">
                  →
                </span>
              </a>
            ) : null}
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
          {c.positioning_v1?.footer_strip_ko ? (
            <p className="enterprise-positioning-footer-strip" role="note">
              {c.positioning_v1.footer_strip_ko}
            </p>
          ) : null}
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
        {c.positioning_v1 ? (
          <>
            <p className="enterprise-positioning-tagline">
              {c.positioning_v1.tagline_ko}
              <span className="enterprise-positioning-tagline-en">
                {" "}
                · {c.positioning_v1.tagline_en}
              </span>
            </p>
            {c.positioning_v1.footer_strip_ko ? (
              <p className="enterprise-positioning-footer-strip">{c.positioning_v1.footer_strip_ko}</p>
            ) : null}
          </>
        ) : null}
        <p className="footer-muted">
          {c.footer.company_line} · {c.footer.brand_subline}
        </p>
        <p className="footer-muted">{c.footer.rights}</p>
      </footer>
    </div>
  );
}
