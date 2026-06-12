"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  type UniverseHubNavGroup,
  type UniverseHubPluginId,
  type UniverseHubPluginV2,
  UNIVERSE_HUB_NAV_GROUP_LABELS,
  visibleUniverseHubPlugins,
} from "@/lib/universeHubPluginsV2";

type Props = {
  activeId?: UniverseHubPluginId;
};

const GROUP_ORDER: UniverseHubNavGroup[] = ["discover", "b2b", "consumer", "ops"];

function isActive(pathname: string, href: string, pluginId: UniverseHubPluginId): boolean {
  if (pluginId === "discover") {
    return pathname === "/hub" || pathname === "/hub/";
  }
  if (href.startsWith("http")) {
    return false;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function renderLink(plugin: UniverseHubPluginV2, pathname: string, activeId?: UniverseHubPluginId) {
  const active = activeId === plugin.id || isActive(pathname, plugin.href, plugin.id);
  const b2bEmphasis = plugin.id === "governed_customization" ? " is-b2b-emphasis" : "";
  const className = active
    ? `universe-hub-sidebar-link is-active${b2bEmphasis}`
    : `universe-hub-sidebar-link${b2bEmphasis}`;
  if (plugin.external) {
    return (
      <a className={className} href={plugin.href} target="_blank" rel="noopener noreferrer">
        {plugin.labelKo}
      </a>
    );
  }
  return (
    <Link className={className} href={plugin.href} aria-current={active ? "page" : undefined}>
      {plugin.labelKo}
    </Link>
  );
}

export function UniverseSidebarV2({ activeId }: Props) {
  const pathname = usePathname() ?? "";
  const plugins = visibleUniverseHubPlugins();

  const byGroup = GROUP_ORDER.map((group) => ({
    group,
    items: plugins.filter((p) => p.navGroup === group),
  })).filter((g) => g.items.length > 0);

  return (
    <aside className="universe-hub-sidebar" aria-label="MKM 플러그인">
      <div className="universe-hub-sidebar-brand">
        <Link href="/hub">JEMA AI</Link>
        <span className="universe-hub-sidebar-tag">Hub</span>
      </div>
      <nav>
        {byGroup.map(({ group, items }) => (
          <div key={group} className="universe-hub-sidebar-group">
            {group !== "discover" ? (
              <p className="universe-hub-sidebar-group-label">
                {UNIVERSE_HUB_NAV_GROUP_LABELS[group as keyof typeof UNIVERSE_HUB_NAV_GROUP_LABELS]}
              </p>
            ) : null}
            <ul className="universe-hub-sidebar-list">
              {items.map((plugin) => (
                <li key={plugin.id}>{renderLink(plugin, pathname, activeId)}</li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <p className="universe-hub-sidebar-foot">
        <Link href="/home">클래식 소개 랜딩</Link>
      </p>
    </aside>
  );
}
