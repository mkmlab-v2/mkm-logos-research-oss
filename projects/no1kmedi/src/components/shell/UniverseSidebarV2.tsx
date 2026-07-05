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
  navGroupLabelForLocale,
  pluginLabelForLocale,
  visibleUniverseHubPlugins,
} from "@/lib/universeHubPluginsV2";
import { useHubLocale } from "@/components/shell/HubLocaleContext";
import { HUB_SHELL_COPY } from "@/lib/universeHubShellCopyV2";

type Props = {
  activeId?: UniverseHubPluginId;
  iconRail?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
};

const GROUP_ORDER: UniverseHubNavGroup[] = ["discover", "b2b", "clinical", "consumer", "ops"];

function isActive(pathname: string, href: string, pluginId: UniverseHubPluginId): boolean {
  if (pluginId === "discover") {
    return pathname === "/hub" || pathname === "/hub/";
  }
  if (href.startsWith("http")) {
    return false;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function hubLayerBadge(pluginId: UniverseHubPluginId): string | null {
  if (pluginId === "national_km_ask") return "L0";
  if (pluginId === "clinician") return "L4";
  return null;
}

function renderLink(
  plugin: UniverseHubPluginV2,
  pathname: string,
  activeId: UniverseHubPluginId | undefined,
  iconRail: boolean | undefined,
  session: ReturnType<typeof useMkmFamilySessionV1>["session"],
  locale: "ko" | "en",
) {
  const href = resolveUniverseHubPluginHref(plugin.id, plugin.href, session);
  const handoff = isMkmFamilyHandoffHref(href);
  const active = activeId === plugin.id || isActive(pathname, plugin.href, plugin.id);
  const b2bEmphasis = plugin.id === "governed_customization" ? " is-b2b-emphasis" : "";
  const className = active
    ? `universe-hub-sidebar-link is-active${b2bEmphasis}${iconRail ? " is-icon-rail" : ""}`
    : `universe-hub-sidebar-link${b2bEmphasis}${iconRail ? " is-icon-rail" : ""}`;
  const label = pluginLabelForLocale(plugin, locale);
  const layerBadge = hubLayerBadge(plugin.id);
  const hypoBadge = plugin.navGroup === "consumer" ? "[HYPO]" : null;

  if (plugin.external || handoff) {
    return (
      <a
        className={className}
        href={href}
        {...(handoff ? {} : { target: "_blank", rel: "noopener noreferrer" })}
        title={layerBadge ? `${label} · ${layerBadge}` : label}
        aria-label={label}
      >
        {iconRail ? (
          <HubPluginIcon pluginId={plugin.id} />
        ) : (
          <span className="universe-hub-sidebar-link-inner">
            <span>{label}</span>
            {layerBadge ? <span className="universe-hub-lane-badge universe-hub-lane-badge--clinical">{layerBadge}</span> : null}
            {hypoBadge ? <span className="universe-hub-lane-badge universe-hub-lane-badge--hypo">{hypoBadge}</span> : null}
          </span>
        )}
      </a>
    );
  }
  return (
    <Link
      className={className}
      href={plugin.href}
      aria-current={active ? "page" : undefined}
      title={iconRail ? label : layerBadge ? `${label} · ${layerBadge}` : undefined}
      aria-label={iconRail ? label : undefined}
    >
      {iconRail ? (
        <HubPluginIcon pluginId={plugin.id} />
      ) : (
        <span className="universe-hub-sidebar-link-inner">
          <span>{label}</span>
          {layerBadge ? <span className="universe-hub-lane-badge universe-hub-lane-badge--clinical">{layerBadge}</span> : null}
          {hypoBadge ? <span className="universe-hub-lane-badge universe-hub-lane-badge--hypo">{hypoBadge}</span> : null}
        </span>
      )}
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
  const { locale } = useHubLocale();
  const shell = HUB_SHELL_COPY[locale];
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
    <aside className={asideClass} aria-label={shell.sidebar_aria}>
      {onToggleCollapse ? (
        <button
          type="button"
          className="universe-hub-sidebar-collapse"
          onClick={onToggleCollapse}
          aria-expanded={!collapsed}
          aria-label={collapsed ? shell.sidebar_expand : shell.sidebar_collapse}
          title={collapsed ? shell.sidebar_expand : shell.sidebar_collapse}
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
          <div
            key={group}
            className={`universe-hub-sidebar-group${group === "consumer" ? " universe-hub-sidebar-group--consumer" : ""}`}
          >
            {!iconRail && group !== "discover" ? (
              <p className="universe-hub-sidebar-group-label">
                {navGroupLabelForLocale(group as Exclude<UniverseHubNavGroup, "discover">, locale)}
              </p>
            ) : null}
            <ul className="universe-hub-sidebar-list">
              {items.map((plugin) => (
                <li key={plugin.id}>{renderLink(plugin, pathname, activeId, iconRail, session, locale)}</li>
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
          <Link href="/home">{shell.classic_landing}</Link>
        </p>
      ) : null}
    </aside>
  );
}
