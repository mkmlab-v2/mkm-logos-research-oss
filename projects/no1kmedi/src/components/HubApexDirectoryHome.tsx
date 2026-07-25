import { siteCopy } from "@/content/siteCopy";
import type { HubLink, SiteCopy } from "@/content/siteCopy";
import { HubApexHeader } from "@/components/HubApexHeader";

type HubKey = keyof SiteCopy["hub_links"];

const FALLBACK_KEYS: HubKey[] = [
  "b2b_acodeai",
  "jema_os_enterprise",
  "clinician_no1kmedi_portal",
  "research_logos",
  "research_mkmlab",
  "showroom_jemaai",
  "premium_mkmlife",
  "personadiary_preview",
];

type DirItem = {
  key: HubKey;
  href: string;
  label: string;
  blurb?: string;
};

type DirGroup = {
  id: string;
  label: string;
  items: DirItem[];
};

function resolveDirectoryGroups(
  apex: NonNullable<SiteCopy["hub_apex"]>,
  hubLinks: SiteCopy["hub_links"],
): DirGroup[] {
  if (apex.directory.groups?.length) {
    const groups: DirGroup[] = [];
    for (const group of apex.directory.groups) {
      const items: DirItem[] = [];
      for (const item of group.items) {
        const key = item.key as HubKey;
        const link = hubLinks[key] as HubLink | undefined;
        if (!link?.href) continue;
        items.push({
          key,
          href: link.href,
          label: item.label || link.label,
          blurb: item.blurb,
        });
      }
      if (items.length) {
        groups.push({ id: group.id, label: group.label, items });
      }
    }
    return groups;
  }

  const keyList = (apex.directory.keys.length ? apex.directory.keys : FALLBACK_KEYS) as HubKey[];
  const items: DirItem[] = [];
  for (const key of keyList) {
    const link = hubLinks[key] as HubLink | undefined;
    if (!link?.href) continue;
    items.push({
      key,
      href: link.href,
      label: link.label,
      blurb: link.sublabel,
    });
  }
  return [{ id: "all", label: apex.directory.section_label, items }];
}

/**
 * Thin brand hub for jema-ai.com `/` — directory only.
 * Ask chrome stays on `/hub`. Classic Ring 0 marketing stays on `/home`.
 */
export function HubApexDirectoryHome() {
  const c = siteCopy;
  const apex = c.hub_apex;
  if (!apex) {
    throw new Error("public-copy.json: hub_apex is required for apex directory home");
  }
  if (!apex.nav) {
    throw new Error("public-copy.json: hub_apex.nav is required for apex guest GNB");
  }

  const groups = resolveDirectoryGroups(apex, c.hub_links);

  return (
    <div className="preset-stripe-linear hub-apex">
      <a className="skip" href="#main">
        {c.homepage_a11y.skip_to_main}
      </a>
      <HubApexHeader nav={apex.nav} brand={c.header} />
      <main id="main">
        <section className="hub-apex-hero" id="top" aria-labelledby="hub-apex-title">
          <p className="hub-apex-brand">{apex.brand}</p>
          <h1 id="hub-apex-title">{apex.title}</h1>
          <p className="hub-apex-lead">{apex.lead}</p>
          <div className="hub-apex-cta">
            <a className="btn btn-primary" href={apex.cta_primary.href}>
              {apex.cta_primary.label}
            </a>
            <a className="btn btn-ghost" href={apex.cta_secondary.href}>
              {apex.cta_secondary.label}
            </a>
            {apex.cta_ask_router ? (
              <a className="btn btn-ghost" href={apex.cta_ask_router.href}>
                {apex.cta_ask_router.label}
              </a>
            ) : null}
          </div>
        </section>

        <section className="hub-apex-section" id="surfaces" aria-labelledby="hub-apex-surfaces-title">
          <h2 id="hub-apex-surfaces-title">{apex.directory.section_label}</h2>
          <p className="section-lead">{apex.directory.section_lead}</p>
          <div className="hub-apex-dir-groups">
            {groups.map((group) => (
              <div key={group.id} className="hub-apex-dir-group" aria-labelledby={`hub-apex-g-${group.id}`}>
                <h3 id={`hub-apex-g-${group.id}`} className="hub-apex-dir-group-label">
                  {group.label}
                </h3>
                <ul className="hub-apex-directory">
                  {group.items.map((item) => {
                    const external = item.href.startsWith("http");
                    return (
                      <li key={item.key}>
                        <a
                          className="hub-apex-dir-tile"
                          href={item.href}
                          {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                        >
                          <span className="hub-apex-dir-label">{item.label}</span>
                          {item.blurb ? <span className="hub-apex-dir-sub">{item.blurb}</span> : null}
                        </a>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </section>
      </main>
      <footer className="hub-apex-footer">
        <p className="hub-apex-footer-note">{apex.footer_note}</p>
        <p className="hub-apex-footer-trust">{apex.trust_thin.body}</p>
        <ul className="hub-apex-footer-bullets" aria-label={apex.anti_merge.section_label}>
          {apex.anti_merge.bullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </footer>
    </div>
  );
}
