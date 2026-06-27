import { siteCopy } from "@/content/siteCopy";

export type HubDiscoverLocale = "ko" | "en";

type HubDiscoverStrings = {
  title: string;
  tagline: string;
  trustWedge: string;
  lead: string;
  placeholder: string;
  submit: string;
  focusBadge: string;
  attachHint: string;
  attachHintTitle: string;
  routingNote: string;
  b2bPrefix: string;
  b2bLink: string;
  localeToggle: string;
  validationMissing: string;
};

function mapLocale(locale: HubDiscoverLocale): HubDiscoverStrings {
  const block = siteCopy.hub_discover?.[locale];
  if (!block) {
    throw new Error(`public-copy.json: hub_discover.${locale} is required`);
  }
  return {
    title: block.title,
    tagline: block.tagline,
    trustWedge: block.trust_wedge ?? "",
    lead: block.lead,
    placeholder: block.placeholder,
    submit: block.submit,
    focusBadge: block.focus_badge,
    attachHint: block.attach_hint,
    attachHintTitle: block.attach_hint_title,
    routingNote: block.routing_note,
    b2bPrefix: block.b2b_prefix,
    b2bLink: block.b2b_link,
    localeToggle: block.locale_toggle,
    validationMissing: block.validation_missing,
  };
}

export const HUB_DISCOVER_COPY: Record<HubDiscoverLocale, HubDiscoverStrings> = {
  ko: mapLocale("ko"),
  en: mapLocale("en"),
};
