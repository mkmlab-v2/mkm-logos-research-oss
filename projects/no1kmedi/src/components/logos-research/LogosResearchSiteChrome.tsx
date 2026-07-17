import { logosResearchCopy } from "@/content/logosResearchCopy";

type Props = {
  active?: "home" | "ask" | "studio" | "docs" | "insight-mobile";
  /** Studio omni/workspace: product-brand chrome — no hub nav or JEMA AI legal line. */
  studioFocus?: boolean;
};

type NavCopy = {
  skip?: string;
  home?: string;
  ask?: string;
  insight_mobile?: string;
  docs?: string;
  studio?: string;
  studio_note?: string;
};

export function LogosResearchSiteChrome({ active = "home", studioFocus = false }: Props) {
  const c = logosResearchCopy;
  const nav = (c.nav ?? {}) as NavCopy;
  const legalLine =
    studioFocus && "legalStudio" in c.brand && typeof c.brand.legalStudio === "string"
      ? c.brand.legalStudio
      : c.brand.legal;
  return (
    <>
      <a className="skip" href="#main">
        {nav.skip ?? "본문으로 건너뛰기"}
      </a>
      <header className="lr-header">
        <div className="lr-header-inner">
          <a className="lr-brand" href="/logos-research">
            <span className="lr-brand-title">{c.brand.productShort}</span>
            <span className="lr-brand-line">{c.brand.productLine}</span>
            <small>{legalLine}</small>
          </a>
          <nav className="lr-nav" aria-label="LOGOS scripture research">
            <a
              className="lr-nav-primary"
              href="/logos-research/ask"
              aria-current={active === "ask" ? "page" : undefined}
            >
              {nav.ask ?? "베타 Q&A"}
            </a>
            <a href="/logos-research" aria-current={active === "home" ? "page" : undefined}>
              {nav.home ?? "소개"}
            </a>
            <a href="/logos-research/docs" aria-current={active === "docs" ? "page" : undefined}>
              {nav.docs ?? "문서"}
            </a>
            <a
              className="lr-nav-muted lr-nav-advanced"
              href="/logos-research/studio"
              aria-current={active === "studio" ? "page" : undefined}
              title={nav.studio_note ?? "베타 후 · OSS 검증 후"}
            >
              {nav.studio ?? "Studio · 베타 후"}
            </a>
          </nav>
        </div>
      </header>
    </>
  );
}
