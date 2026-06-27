import { logosResearchCopy } from "@/content/logosResearchCopy";

type Props = {
  active?: "home" | "studio" | "docs";
};

export function LogosResearchSiteChrome({ active = "home" }: Props) {
  const c = logosResearchCopy;
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
            <small>{c.brand.legal}</small>
          </a>
          <nav className="lr-nav" aria-label="Logos research">
            <a href="/logos-research/docs" aria-current={active === "docs" ? "page" : undefined}>
              {c.nav?.docs ?? "문서"}
            </a>
            <a
              href="/logos-research/studio"
              aria-current={active === "studio" ? "page" : undefined}
            >
              {c.nav?.studio ?? "스튜디오"}
            </a>
            <a href="/logos-research#metrics">{c.nav?.metrics ?? "지표"}</a>
            <a href="/logos-research#tiers">{c.nav?.tiers ?? "티어"}</a>
            <a className="lr-nav-muted" href={c.footer.hub}>
              {c.footer.hub_label}
            </a>
          </nav>
        </div>
      </header>
    </>
  );
}
