import Link from "next/link";

import { logosResearchCopy } from "@/content/logosResearchCopy";
import { logosResearchDocsCopy } from "@/content/logosResearchDocsCopy";
import { DEFAULT_HOMEPAGE_PRESET, homepagePresetClassMap } from "@/lib/homepagePreset";

type Props = {
  children: React.ReactNode;
  activeId?: string;
};

export function LogosResearchDocsShell({ children, activeId }: Props) {
  const c = logosResearchCopy;
  const docs = logosResearchDocsCopy;
  const presetClass = homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];

  return (
    <div className={`${presetClass} logos-research-page logos-research-docs`}>
      <a className="skip" href="#main">
        Skip to main
      </a>

      <header className="lr-header">
        <div className="lr-header-inner">
          <Link className="lr-brand" href="/logos-research">
            <span className="lr-brand-title">{c.brand.productShort}</span>
            <span className="lr-brand-line">{c.brand.productLine}</span>
            <small>{c.brand.legal}</small>
          </Link>
          <nav className="lr-nav" aria-label="Logos docs">
            <Link href="/logos-research">Home</Link>
            <Link href={docs.nav.docs_hub} aria-current={activeId === "hub" ? "page" : undefined}>
              Docs
            </Link>
            {docs.nav.items.map((item) => (
              <Link
                key={item.id}
                href={item.href}
                aria-current={activeId === item.id ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
            <a className="lr-nav-muted" href={docs.demo_url} rel="noopener noreferrer">
              Live demo
            </a>
          </nav>
        </div>
      </header>

      <main id="main" className="lr-docs-main">
        {children}
      </main>

      <footer className="lr-docs-footer">
        <p className="lr-docs-footer-ko">{docs.footer_disclaimer.ko}</p>
        <p className="lr-docs-footer-en">{docs.footer_disclaimer.en}</p>
        <p className="lr-docs-footer-links">
          <Link href="/logos-research">Workspace home</Link>
          {" · "}
          <a href={docs.demo_url} rel="noopener noreferrer">
            Graph Studio demo
          </a>
          {" · "}
          <a href={c.footer.hub}>{c.footer.hub_label}</a>
        </p>
      </footer>
    </div>
  );
}

export function DocsPageHeader({
  eyebrow,
  title,
  lead,
}: {
  eyebrow?: string;
  title: string;
  lead?: string;
}) {
  return (
    <header className="lr-docs-page-header">
      {eyebrow ? <p className="lr-eyebrow">{eyebrow}</p> : null}
      <h1>{title}</h1>
      {lead ? <p className="lr-section-lead">{lead}</p> : null}
    </header>
  );
}
