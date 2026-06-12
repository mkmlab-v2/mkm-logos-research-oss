"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { HubAccountEntryV1 } from "@/components/shell/HubAccountEntryV1";
import { HubBrandMark, HubPluginIcon } from "@/components/shell/HubPluginIcon";
import { useMkmFamilySessionV1 } from "@/hooks/useMkmFamilySessionV1";
import {
  isMkmFamilyHandoffHref,
  resolveUniverseHubPluginHref,
} from "@/lib/mkmFamilyHandoffV1";
import {
  type UniverseHubNavGroup,
  type UniverseHubPluginId,
  type UniverseHubPluginV2,
  UNIVERSE_HUB_NAV_GROUP_LABELS,
  visibleUniverseHubPlugins,
} from "@/lib/universeHubPluginsV2";

type Props = {
  activeId?: UniverseHubPluginId;
  iconRail?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
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

function renderLink(
  plugin: UniverseHubPluginV2,
  pathname: string,
  activeId: UniverseHubPluginId | undefined,
  iconRail: boolean | undefined,
  session: ReturnType<typeof useMkmFamilySessionV1>["session"],
) {
  const href = resolveUniverseHubPluginHref(plugin.id, plugin.href, session);
  const handoff = isMkmFamilyHandoffHref(href);
  const active = activeId === plugin.id || isActive(pathname, plugin.href, plugin.id);
  const b2bEmphasis = plugin.id === "governed_customization" ? " is-b2b-emphasis" : "";
  const className = active
    ? `universe-hub-sidebar-link is-active${b2bEmphasis}${iconRail ? " is-icon-rail" : ""}`
    : `universe-hub-sidebar-link${b2bEmphasis}${iconRail ? " is-icon-rail" : ""}`;
  const label = plugin.labelKo;

  if (plugin.external || handoff) {
    return (
      <a
        className={className}
        href={href}
        {...(handoff ? {} : { target: "_blank", rel: "noopener noreferrer" })}
        title={label}
        aria-label={label}
      >
        {iconRail ? <HubPluginIcon pluginId={plugin.id} /> : label}
      </a>
    );
  }
  return (
    <Link
      className={className}
      href={plugin.href}
      aria-current={active ? "page" : undefined}
      title={iconRail ? label : undefined}
      aria-label={iconRail ? label : undefined}
    >
      {iconRail ? <HubPluginIcon pluginId={plugin.id} /> : label}
    </Link>
  );
}

export function UniverseSidebarV2({
  activeId,
  iconRail = false,
  collapsed = false,
  onToggleCollapse,
}: Props) {
  const pathname = usePathname() ?? "";
  const { session } = useMkmFamilySessionV1();
  const plugins = visibleUniverseHubPlugins();

  const byGroup = GROUP_ORDER.map((group) => ({
    group,
    items: plugins.filter((p) => p.navGroup === group),
  })).filter((g) => g.items.length > 0);

  const asideClass = iconRail
    ? "universe-hub-sidebar universe-hub-sidebar--icon-rail"
    : "universe-hub-sidebar";

  return (
    <aside className={asideClass} aria-label="MKM 플러그인">
      {onToggleCollapse ? (
        <button
          type="button"
          className="universe-hub-sidebar-collapse"
          onClick={onToggleCollapse}
          aria-expanded={!collapsed}
          aria-label={collapsed ? "사이드바 펼치기" : "사이드바 접기"}
          title={collapsed ? "사이드바 펼치기" : "사이드바 접기"}
        >
          {collapsed ? "›" : "‹"}
        </button>
      ) : null}
      {iconRail ? (
        <div className="universe-hub-sidebar-brand universe-hub-sidebar-brand--icon-rail">
          <Link href="/hub" title="JEMA AI Hub" aria-label="JEMA AI Hub">
            <HubBrandMark />
          </Link>
        </div>
      ) : (
        <div className="universe-hub-sidebar-brand">
          <Link href="/hub">JEMA AI</Link>
          <span className="universe-hub-sidebar-tag">Hub</span>
        </div>
      )}
      <nav>
        {byGroup.map(({ group, items }) => (
          <div key={group} className="universe-hub-sidebar-group">
            {!iconRail && group !== "discover" ? (
              <p className="universe-hub-sidebar-group-label">
                {UNIVERSE_HUB_NAV_GROUP_LABELS[group as keyof typeof UNIVERSE_HUB_NAV_GROUP_LABELS]}
              </p>
            ) : null}
            <ul className="universe-hub-sidebar-list">
              {items.map((plugin) => (
                <li key={plugin.id}>{renderLink(plugin, pathname, activeId, iconRail, session)}</li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      <div className="universe-hub-sidebar-account">
        <HubAccountEntryV1 compact={iconRail} />
      </div>
      {!iconRail ? (
        <p className="universe-hub-sidebar-foot">
          <Link href="/home">클래식 소개 랜딩</Link>
        </p>
      ) : null}
    </aside>
  );
}
