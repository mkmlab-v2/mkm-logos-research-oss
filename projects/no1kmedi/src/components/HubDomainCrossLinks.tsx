import type { HubLink, SiteCopy } from "@/content/siteCopy";
import type { HubDiscoverLocale } from "@/lib/universeHubDiscoverCopyV2";
import { resolveHubLinkLabel } from "@/lib/universeHubShellCopyV2";

export const HUB_PRIMARY_KEYS = [
  "lane_governance",
  "validation_engine",
  "showroom_jemaai",
  "jema_os_enterprise",
  "premium_mkmlife",
  "clinician_support",
  "clinician_no1kmedi_portal",
  "mai_profile_card",
  "b2b_acodeai",
  "farm_b2b_smartfarm",
  "research_logos",
  "research_mkmlab",
  "personadiary_preview",
  "memory_continuity_preview",
] as const;

export const HUB_SECONDARY_KEYS = [] as const;

export const HUB_FOOTER_KEYS = [
  "jema_os_enterprise",
  "logos_beta_ask",
  "research_logos",
  "evidence_pack_v0",
  "premium_mkmlife",
  "b2b_acodeai",
  "research_mkmlab",
  "clinician_support",
] as const;

/** Legacy demos — folded footer only (not primary reviewer path). */
export const HUB_LEGACY_FOOTER_KEYS = ["showroom_jemaai"] as const;

type HubKey = keyof SiteCopy["hub_links"];

/** Four-group ecosystem footer (roadmap P4). */
export const HUB_FOOTER_GROUPS: Array<{
  id: string;
  label_ko: string;
  label_en: string;
  keys: readonly HubKey[];
}> = [
  {
    id: "patient_clinical",
    label_ko: "환자·임상",
    label_en: "Patient · clinical",
    keys: [
      "clinician_support",
      "mai_profile_card",
      "personadiary_preview",
      "memory_continuity_preview",
      "gyeokmul_preview",
    ],
  },
  {
    id: "physician_b2b",
    label_ko: "한의사·B2B",
    label_en: "Physician · B2B",
    keys: ["jema_os_enterprise", "clinician_no1kmedi_portal", "b2b_acodeai", "evidence_pack_v0"],
  },
  {
    id: "research",
    label_ko: "연구·관측",
    label_en: "Research · observe",
    keys: ["research_logos", "logos_beta_ask", "research_mkmlab", "showroom_jemaai"],
  },
  {
    id: "developer",
    label_ko: "소비자·개발",
    label_en: "Consumer · dev",
    keys: ["premium_mkmlife", "compression_roi_dashboard", "wtt_persona_os_demo"],
  },
];

type Props = {
  hubLinks: SiteCopy["hub_links"];
  keys: readonly HubKey[];
  locale?: HubDiscoverLocale;
  ariaLabel?: string;
  className?: string;
};

function HubPillLink({
  link,
  locale = "ko",
}: {
  link: HubLink;
  locale?: HubDiscoverLocale;
}) {
  const external = link.href.startsWith("http");
  const label = resolveHubLinkLabel(link, locale);
  return (
    <a
      className="hub-pill-link"
      href={link.href}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      title={locale === "en" && link.sublabel_en ? link.sublabel_en : link.sublabel}
    >
      {label}
    </a>
  );
}

export function HubDomainCrossLinks({
  hubLinks,
  keys,
  locale = "ko",
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
        <HubPillLink key={key} link={link} locale={locale} />
      ))}
    </nav>
  );
}
