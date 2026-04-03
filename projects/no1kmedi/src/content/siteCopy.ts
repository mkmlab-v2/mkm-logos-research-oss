import data from "../../marketing-site/public-copy.json";

export type SiteCopy = {
  seo: { title: string; description: string };
  nav: { about: string; safety: string; workflow: string; contact: string };
  hero: {
    eyebrow: string;
    title: string;
    subtitle: string;
    cta_primary: string;
    cta_secondary: string;
  };
  about: { title: string; section_lead: string };
  value_props: { title: string; body: string }[];
  safety: { title: string; items: string[] };
  workflow: { title: string; section_lead: string; steps: string[] };
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
