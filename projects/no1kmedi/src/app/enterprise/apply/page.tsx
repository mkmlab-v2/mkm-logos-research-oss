import type { Metadata } from "next";
import Link from "next/link";
import { CompressionPilotAuditApplyForm } from "@/components/CompressionPilotAuditApplyForm";
import { siteCopy } from "@/content/siteCopy";
import { DEFAULT_HOMEPAGE_PRESET, homepagePresetClassMap } from "@/lib/homepagePreset";

function requireApplyCopy() {
  const copy = siteCopy.compression_pilot_audit_apply;
  if (!copy) {
    throw new Error("public-copy.json: compression_pilot_audit_apply block required");
  }
  return copy;
}

export function generateMetadata(): Metadata {
  const copy = requireApplyCopy();
  return {
    title: copy.seo.title,
    description: copy.seo.description,
  };
}

export default function EnterprisePilotAuditApplyPage() {
  const copy = requireApplyCopy();
  const c = siteCopy;
  const presetClass = homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];

  return (
    <div className={`${presetClass} enterprise-page enterprise-apply-page`}>
      <a className="skip" href="#main">
        {c.homepage_a11y.skip_to_main}
      </a>
      <header className="site-header enterprise-header">
        <div className="header-inner">
          <Link className="brand" href="/enterprise">
            {c.header.brand_name} <span>{copy.hero.eyebrow}</span>
          </Link>
          <nav className="nav-main enterprise-nav" aria-label="파일럿 신청">
            <Link href="/enterprise">{copy.nav.back_enterprise}</Link>
            <Link href="/hub">{copy.nav.back_hub}</Link>
          </nav>
        </div>
      </header>

      <main id="main" className="enterprise-apply-main">
        <section className="enterprise-apply-hero" aria-labelledby="apply-title">
          <span className="eyebrow enterprise-eyebrow">{copy.hero.eyebrow}</span>
          <h1 id="apply-title">{copy.hero.title}</h1>
          <p className="hero-lead">{copy.hero.subtitle}</p>
          <div className="enterprise-apply-steps" aria-labelledby="apply-steps-label">
            <h2 id="apply-steps-label" className="enterprise-apply-steps-title">
              {copy.hero.steps_label}
            </h2>
            <ol>
              {copy.hero.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        </section>

        <section className="enterprise-apply-form-wrap" aria-labelledby="apply-form-heading">
          <h2 id="apply-form-heading" className="sr-only">
            신청 양식
          </h2>
          <CompressionPilotAuditApplyForm copy={copy} />
        </section>

        <section className="enterprise-disclaimer enterprise-apply-disclaimer" aria-labelledby="apply-disclaimer">
          <h2 id="apply-disclaimer">{copy.disclaimer.title}</h2>
          <ul>
            {copy.disclaimer.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="site-footer enterprise-footer">
        <p>
          <Link href="/enterprise">/enterprise</Link> · <Link href="/hub">/hub</Link> ·{" "}
          <a href={`mailto:${c.footer.email}`}>{c.footer.email}</a>
        </p>
        <p className="footer-muted">{c.footer.rights}</p>
      </footer>
    </div>
  );
}
