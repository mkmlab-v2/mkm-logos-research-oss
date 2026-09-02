import { siteCopy } from "@/content/siteCopy";
import type { HubDiscoverLocale } from "@/lib/universeHubDiscoverCopyV2";

export type HubShellCopy = {
  sidebar_aria: string;
  sidebar_expand: string;
  sidebar_collapse: string;
  classic_landing: string;
  footer_ecosystem: string;
  footer_legacy: string;
  footer_links_aria: string;
  footer_legacy_aria: string;
  hub_loading: string;
  intent_group_aria: string;
  inspector_title: string;
  inspector_lead: string;
  inspector_artifacts_heading: string;
  inspector_meta: string;
  inspector_studio_cta: string;
  inspector_topology_loaded: string;
  inspector_topology_missing: string;
  inspector_logos_more: string;
  inspector_logos_topology_heading: string;
  inspector_corpus_snapshot: string;
  inspector_hub_candidates_empty: string;
  inspector_topology_file_missing: string;
  inspector_b2b_heading: string;
  inspector_link_compression: string;
  inspector_link_logos: string;
  inspector_link_life: string;
  inspector_link_customize: string;
};

function mapShell(locale: HubDiscoverLocale): HubShellCopy {
  const block = siteCopy.hub_shell?.[locale];
  if (!block) {
    throw new Error(`public-copy.json: hub_shell.${locale} is required`);
  }
  return block as HubShellCopy;
}

export const HUB_SHELL_COPY: Record<HubDiscoverLocale, HubShellCopy> = {
  ko: mapShell("ko"),
  en: mapShell("en"),
};

export function resolveHubLinkLabel(
  link: { label: string; label_en?: string },
  locale: HubDiscoverLocale,
): string {
  if (locale === "en" && link.label_en) return link.label_en;
  return link.label;
}
