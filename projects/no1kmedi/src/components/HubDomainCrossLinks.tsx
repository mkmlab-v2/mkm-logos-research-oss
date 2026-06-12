import type { HubLink, SiteCopy } from "@/content/siteCopy";

export const HUB_PRIMARY_KEYS = [
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

export const HUB_SECONDARY_KEYS = [] as const;

export const HUB_FOOTER_KEYS = [
  "showroom_jemaai",
  "premium_mkmlife",
  "b2b_acodeai",
  "research_mkmlab",
  "clinician_support",
] as const;

type HubKey = keyof SiteCopy["hub_links"];

type Props = {
  hubLinks: SiteCopy["hub_links"];
  keys: readonly HubKey[];
  ariaLabel?: string;
  className?: string;
};

function HubPillLink({ link }: { link: HubLink }) {
  const external = link.href.startsWith("http");
  return (
    <a
      className="hub-pill-link"
      href={link.href}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      title={link.sublabel}
    >
      {link.label}
    </a>
  );
}

export function HubDomainCrossLinks({
  hubLinks,
  keys,
  ariaLabel = "MKM 관련 도메인 안내",
  className = "hub-cross-links",
}: Props) {
  const items = keys
    .map((key) => ({ key, link: hubLinks[key] }))
    .filter((row): row is { key: HubKey; link: HubLink } => Boolean(row.link?.href));

  if (!items.length) return null;

  return (
    <nav className={className} aria-label={ariaLabel}>
      {items.map(({ key, link }) => (
        <HubPillLink key={key} link={link} />
      ))}
    </nav>
  );
}
