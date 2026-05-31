import type { HubLink, SiteCopy } from "@/content/siteCopy";

const HUB_PRIMARY_KEYS = [
  "showroom_jemaai",
  "premium_mkmlife",
  "clinician_support",
  "clinician_no1kmedi_portal",
  "mai_profile_card",
  "b2b_acodeai",
  "farm_b2b_smartfarm",
  "research_mkmlab",
  "personadiary_preview",
] as const;

const HUB_SECONDARY_KEYS = [
  "showroom_meaning_qa_v2",
  "showroom_topology_radar",
  "showroom_meaning_graph",
] as const;

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

function HubLinkButton({ link }: { link: HubLink }) {
  return (
    <a
      className="btn btn-ghost"
      href={link.href}
      target="_blank"
      rel="noopener noreferrer"
      title={link.sublabel}
    >
      {link.label}
    </a>
  );
}

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
      <div className="section-cta hub-cross-links" aria-label="MKM 관련 도메인 안내">
        {HUB_PRIMARY_KEYS.map((key) => {
          const link = hubLinks[key];
          if (!link?.href) return null;
          return <HubLinkButton key={key} link={link} />;
        })}
        {HUB_SECONDARY_KEYS.map((key) => {
          const link = hubLinks[key];
          if (!link?.href) return null;
          return <HubLinkButton key={key} link={link} />;
        })}
      </div>
    </section>
  );
}
