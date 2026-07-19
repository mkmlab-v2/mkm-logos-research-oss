import { SmartfarmBrandLogo } from "@/components/smartfarm/SmartfarmBrandLogo";
import { SystemFlowDiagram } from "@/components/smartfarm/SystemFlowDiagram";
import { smartfarmCopy } from "@/content/smartfarmCopy";
import { DEFAULT_HOMEPAGE_PRESET, homepagePresetClassMap } from "@/lib/homepagePreset";

const c = smartfarmCopy;
const presetClass = homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];

export default function SmartfarmPage() {
  const mailSubject = encodeURIComponent(c.a11y.mail_subject);
  const mailHref = `mailto:${c.contact.email}?subject=${mailSubject}`;

  return (
    <div className={`${presetClass} smartfarm-page`}>
      <a className="skip" href="#main">
        {c.a11y.skip_to_main}
      </a>

      <header className="sf-header">
        <div className="sf-header-inner">
          <a className="sf-brand" href="/smartfarm">
            <span className="sf-brand-logo" aria-hidden="true">
              <SmartfarmBrandLogo variant="header" />
            </span>
            <span className="sf-brand-text">
              <span className="sf-brand-title">
                <span className="sf-brand-mkm">{c.brand.productShort}</span>
                <span className="sf-brand-line">{c.brand.productLine}</span>
              </span>
              <small>{c.brand.legal}</small>
            </span>
          </a>
          <nav className="sf-nav" aria-label={c.a11y.nav_aria_label}>
            <a href="#flow">{c.nav.flow}</a>
            <a href="#architecture">{c.nav.architecture}</a>
            <a href="#comms">{c.nav.comms}</a>
            <a href="#roles">{c.nav.roles}</a>
            <a href="#scope">{c.nav.scope}</a>
            <a href="#scale">{c.nav.scale}</a>
            <a href="#partnership">{c.nav.partnership}</a>
            <a href="#pilot">{c.nav.pilot}</a>
            <a href="/smartfarm/operator">{c.nav.operator}</a>
            <a href="/smartfarm/nojisim">{c.nav.nojisim}</a>
            <a href="/smartfarm/palmpalm">{c.nav.palmpalm}</a>
            <a href="#contact">{c.nav.contact}</a>
            <a className="sf-nav-muted" href={c.footer.hub}>
              {c.nav.enterprise}
            </a>
          </nav>
        </div>
      </header>

      <main id="main">
        <section className="sf-hero" aria-labelledby="sf-hero-title">
          <div className="sf-hero-bg" aria-hidden="true" />
          <div className="sf-hero-grid" aria-hidden="true" />
          <p className="sf-eyebrow">{c.hero.eyebrow}</p>
          <p className="sf-public-url">
            <span className="sf-public-url-label">B2B</span>
            <a href={c.publicUrl}>{c.publicUrl.replace("https://", "")}</a>
          </p>
          <h1 id="sf-hero-title">
            {c.hero.title.split("\n").map((line, i) => (
              <span key={line}>
                {i > 0 ? <br /> : null}
                {line}
              </span>
            ))}
          </h1>
          <p className="sf-hero-lead">{c.hero.lead}</p>
          <div className="sf-hero-cta">
            <a className="sf-btn sf-btn-primary" href={mailHref}>
              {c.hero.cta_primary}
            </a>
            <a className="sf-btn sf-btn-ghost" href="#flow">
              {c.hero.cta_secondary}
            </a>
          </div>
        </section>

        <section id="flow" className="sf-section sf-section--alt" aria-labelledby="sf-flow-title">
          <div className="sf-section-head">
            <h2 id="sf-flow-title">{c.flow.title}</h2>
            <p className="sf-section-lead">{c.flow.lead}</p>
          </div>
          <SystemFlowDiagram />
        </section>

        <section id="architecture" className="sf-section" aria-labelledby="sf-arch-title">
          <div className="sf-section-head">
            <h2 id="sf-arch-title">{c.architecture.title}</h2>
            <p className="sf-section-lead">{c.architecture.lead}</p>
          </div>
          <div className="sf-arch-layout">
            <div
              className="sf-flow-card"
              role="img"
              aria-label="급수 탱크와 양액 탱크에서 각각 밸브를 거쳐 합류한 뒤 여과와 펌프를 통해 점적 관수"
            >
              <div className="sf-flow-row">
                <div className="sf-flow-node sf-flow-node--water">
                  <span>급수 탱크</span>
                  <em>밸브</em>
                </div>
                <div className="sf-flow-join" aria-hidden="true">
                  <span>합류</span>
                </div>
                <div className="sf-flow-node sf-flow-node--nutrient">
                  <span>양액 탱크</span>
                  <em>밸브</em>
                </div>
              </div>
              <div className="sf-flow-pipe" aria-hidden="true" />
              <div className="sf-flow-tail">
                <span>여과 · 펌프</span>
                <span className="sf-flow-tail-end">점적 · 노지</span>
              </div>
            </div>
            <ol className="sf-steps">
              {c.architecture.steps.map((step, index) => (
                <li key={step.label}>
                  <span className="sf-step-num">{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <strong>{step.label}</strong>
                    <p>{step.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
          <div className="sf-spec-grid">
            {c.architecture.specs.map((row) => (
              <div key={row.k} className="sf-spec-item">
                <span className="sf-spec-k">{row.k}</span>
                <span className="sf-spec-v">{row.v}</span>
              </div>
            ))}
          </div>
        </section>

        <section id="comms" className="sf-section sf-section--alt" aria-labelledby="sf-comms-title">
          <div className="sf-section-head">
            <h2 id="sf-comms-title">{c.comms.title}</h2>
            <p className="sf-section-lead">{c.comms.lead}</p>
          </div>
          <div className="sf-comms-stack" role="img" aria-label="센서에서 게이트웨이까지 무선, 게이트웨이에서 LTE로 서버 연결">
            {c.comms.layers.map((layer, index) => (
              <article key={layer.label} className="sf-comms-layer">
                <span className="sf-comms-step">{index + 1}</span>
                <div>
                  <strong>{layer.label}</strong>
                  <p>{layer.detail}</p>
                </div>
                <span className="sf-comms-tag">{layer.tag}</span>
              </article>
            ))}
            <div className="sf-comms-arrow" aria-hidden="true">
              <span>→</span>
              <span>MKM 서버 · 운영 앱</span>
            </div>
          </div>
          <p className="sf-comms-note">{c.comms.note}</p>
        </section>

        <section id="roles" className="sf-section" aria-labelledby="sf-roles-title">
          <div className="sf-section-head">
            <h2 id="sf-roles-title">{c.roles.title}</h2>
            <p className="sf-section-lead">{c.roles.lead}</p>
          </div>
          <div className="sf-roles-grid">
            {c.roles.items.map((item, index) => (
              <article key={item.who} className="sf-role-card">
                <span className="sf-role-step" aria-hidden="true">
                  {index + 1}
                </span>
                <span className="sf-role-tag">{item.tag}</span>
                <h3>{item.who}</h3>
                <p>{item.scope}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="scope" className="sf-section sf-section--alt" aria-labelledby="sf-scope-title">
          <div className="sf-section-head">
            <h2 id="sf-scope-title">{c.scope.title}</h2>
            <p className="sf-section-lead">{c.scope.lead}</p>
          </div>
          <div className="sf-scope-table-wrap">
            <table className="sf-scope-table">
              <caption className="sf-sr-only">{c.scope.title}</caption>
              <thead>
                <tr>
                  {c.scope.columns.map((col) => (
                    <th key={col} scope="col">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {c.scope.rows.map(([role, detail]) => (
                  <tr key={role}>
                    <th scope="row">{role}</th>
                    <td>{detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section id="scale" className="sf-section" aria-labelledby="sf-scale-title">
          <div className="sf-section-head">
            <h2 id="sf-scale-title">{c.scale.title}</h2>
            <p className="sf-section-lead">{c.scale.lead}</p>
          </div>
          <div className="sf-scope-table-wrap">
            <table className="sf-scope-table sf-scope-table--scale">
              <caption className="sf-sr-only">{c.scale.title}</caption>
              <thead>
                <tr>
                  {c.scale.columns.map((col) => (
                    <th key={col} scope="col">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {c.scale.rows.map(([label, pilot, expanded]) => (
                  <tr key={label}>
                    <th scope="row">{label}</th>
                    <td>{pilot}</td>
                    <td>{expanded}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="sf-comms-note">{c.scale.note}</p>
        </section>

        <section id="partnership" className="sf-section sf-section--alt" aria-labelledby="sf-part-title">
          <div className="sf-section-head">
            <h2 id="sf-part-title">{c.partnership.title}</h2>
            <p className="sf-section-lead">{c.partnership.lead}</p>
          </div>
          <div className="sf-partner-grid">
            {c.partnership.items.map((item, index) => (
              <article key={item.title} className="sf-partner-card">
                <span className="sf-partner-index" aria-hidden="true">
                  {index + 1}
                </span>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="pilot" className="sf-section" aria-labelledby="sf-pilot-title">
          <div className="sf-pilot-banner">
            <p className="sf-pilot-label">Field pilot</p>
            <h2 id="sf-pilot-title">{c.pilot.title}</h2>
            <p className="sf-pilot-site">{c.pilot.site}</p>
            <p className="sf-pilot-status">
              <span className="sf-pilot-dot" aria-hidden="true" />
              {c.pilot.status}
            </p>
            <p className="sf-pilot-note">{c.pilot.note}</p>
            <div className="sf-hero-cta" style={{ marginTop: "1rem" }}>
              <a className="sf-btn sf-btn-primary" href="/smartfarm/nojisim">
                노지심 (운영·승인)
              </a>
              <a className="sf-btn sf-btn-ghost" href="/smartfarm/palmpalm">
                팜팜팜 (손님)
              </a>
            </div>
            <p className="sf-pilot-note" style={{ marginTop: "0.75rem" }}>
              참조용 MVP · Go-Live·상용 완료 아님 · 요청≠자동 관수
            </p>
          </div>
        </section>

        <section id="contact" className="sf-section sf-contact" aria-labelledby="sf-contact-title">
          <div className="sf-contact-card">
            <h2 id="sf-contact-title">{c.contact.title}</h2>
            <p className="sf-contact-hint">{c.contact.hint}</p>
            <a className="sf-btn sf-btn-primary sf-btn-lg" href={mailHref}>
              {c.contact.email}
            </a>
            <p className="sf-contact-meta">{c.contact.biz_reg}</p>
          </div>
          <div className="sf-disclaimer">
            <h3>{c.disclaimer.title}</h3>
            <ul>
              {c.disclaimer.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>
      </main>

      <footer className="sf-footer">
        <p>
          <a href={c.publicUrl}>farm.jema-ai.com</a>
          <span aria-hidden="true"> · </span>
          <a href={c.footer.home}>jema-ai.com</a>
          <span aria-hidden="true"> · </span>
          <a href={c.footer.hub}>{c.nav.enterprise}</a>
          <span aria-hidden="true"> · </span>
          <a href={mailHref}>{c.contact.email}</a>
        </p>
        <p className="sf-footer-muted">
          {c.brand.legal} · {c.brand.product}
        </p>
        <p className="sf-sr-only" aria-hidden="true">
          {c.contact.email}
        </p>
      </footer>
    </div>
  );
}
