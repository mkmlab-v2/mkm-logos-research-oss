import data from "../../marketing-site/public-copy.json";

export type SiteCopy = {
  header: { brand_name: string; brand_tagline: string };
  seo: { title: string; description: string };
  nav: { about: string; safety: string; workflow: string; contact: string };
  hero: {
    eyebrow: string;
    title: string;
    subtitle: string;
    cta_primary: string;
    cta_secondary: string;
    cta_tertiary: string;
    cta_quaternary: string;
  };
  trust: { items: { label: string; value: string }[]; note: string };
  public_solution: {
    title: string;
    section_lead: string;
    cards: { title: string; body: string }[];
    cta_primary: string;
    cta_secondary: string;
  };
  concept_block: {
    label: string;
    title: string;
    lead: string;
    proof_items: string[];
    stage_label: string;
  };
  about: { title: string; section_lead: string };
  value_props: { title: string; body: string }[];
  safety: { title: string; items: string[] };
  workflow: { title: string; section_lead: string; steps: string[] };
  landing_flow: {
    title: string;
    lead: string;
    cards: { label: string; title: string; body: string }[];
    cta_primary: string;
    cta_secondary: string;
  };
  contact: { title: string; section_lead: string; email_label: string };
  footer: {
    company_line: string;
    address: string;
    email: string;
    biz_reg: string;
    rights: string;
  };
};

export const siteCopy = data as SiteCopy;
