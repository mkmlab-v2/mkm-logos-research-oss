import type { SiteCopy } from "@/content/siteCopy";
import {
  HubDomainCrossLinks,
  HUB_PRIMARY_KEYS,
  HUB_SECONDARY_KEYS,
} from "@/components/HubDomainCrossLinks";

type HomeHeroSectionProps = {
  hero: SiteCopy["hero"];
  hubLinks: SiteCopy["hub_links"];
  ctaLinks: {
    primary: string;
    secondary: string;
    tertiary: string;
    quaternary: string;
  };
};

/** Layer B target: map Figma Hero Auto-layout frame → this component only. */
export function HomeHeroSection({ hero, hubLinks, ctaLinks }: HomeHeroSectionProps) {
  return (
    <section className="hero" id="top" aria-labelledby="hero-title">
      <div className="hero-orb hero-orb-a" aria-hidden="true" />
      <div className="hero-orb hero-orb-b" aria-hidden="true" />
      <div className="hero-grid-overlay" aria-hidden="true" />
      <span className="eyebrow">{hero.eyebrow}</span>
      <h1 id="hero-title">{hero.title}</h1>
      <p className="hero-lead">{hero.subtitle}</p>
      <div className="hero-cta">
        <a className="btn btn-primary" href={ctaLinks.primary}>
          {hero.cta_primary}
        </a>
        <a className="btn btn-ghost" href={ctaLinks.secondary}>
          {hero.cta_secondary}
        </a>
        <a className="btn btn-ghost" href={ctaLinks.tertiary}>
          {hero.cta_tertiary}
        </a>
        <a className="btn btn-ghost" href={ctaLinks.quaternary}>
          {hero.cta_quaternary}
        </a>
      </div>
      <div className="hero-role-cta">
        {hero.role_cards.map((card) => (
          <article key={card.title} className="card card-lift">
            <h3>{card.title}</h3>
            <p>{card.body}</p>
            <a className={`btn ${card.variant === "primary" ? "btn-primary" : "btn-ghost"}`} href={card.href}>
              {card.cta}
            </a>
          </article>
        ))}
      </div>
      <div className="hero-proof" role="list" aria-label={hero.proof_aria_label}>
        {hero.proof_items.map((item) => (
          <span key={item} role="listitem">
            {item}
          </span>
        ))}
      </div>
      <HubDomainCrossLinks hubLinks={hubLinks} keys={HUB_PRIMARY_KEYS} />
      <HubDomainCrossLinks
        hubLinks={hubLinks}
        keys={HUB_SECONDARY_KEYS}
        className="hub-cross-links hub-cross-links--secondary"
        ariaLabel="쇼룸 연구·데모 링크"
      />
    </section>
  );
}
