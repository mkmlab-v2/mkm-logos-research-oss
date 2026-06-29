import { logosResearchCopy } from "@/content/logosResearchCopy";

type Props = {
  active?: "home" | "studio" | "docs";
  /** Studio omni/workspace: LOGOS-first chrome — no hub nav or JEMA AI legal line. */
  studioFocus?: boolean;
};

export function LogosResearchSiteChrome({ active = "home", studioFocus = false }: Props) {
  const c = logosResearchCopy;
  const legalLine =
    studioFocus && "legalStudio" in c.brand && typeof c.brand.legalStudio === "string"
      ? c.brand.legalStudio
      : c.brand.legal;
  return (
    <>
      <a className="skip" href="#main">
        {c.nav?.skip ?? "본문으로 건너뛰기"}
      </a>
      <header className="lr-header">
        <div className="lr-header-inner">
          <a className="lr-brand" href="/logos-research">
            <span className="lr-brand-title">{c.brand.productShort}</span>
            <span className="lr-brand-line">{c.brand.productLine}</span>
            <small>{legalLine}</small>
          </a>
          <nav className="lr-nav" aria-label="Logos research">
            <a href="/logos-research" aria-current={active === "home" ? "page" : undefined}>
              {c.nav?.home ?? "홈"}
            </a>
            <a
              href="/logos-research/studio"
              aria-current={active === "studio" ? "page" : undefined}
            >
              {c.nav?.studio ?? "연구 스튜디오"}
            </a>
            <a href="/logos-research/docs" aria-current={active === "docs" ? "page" : undefined}>
              {c.nav?.docs ?? "학술 라이브러리"}
            </a>
          </nav>
        </div>
      </header>
    </>
  );
}
