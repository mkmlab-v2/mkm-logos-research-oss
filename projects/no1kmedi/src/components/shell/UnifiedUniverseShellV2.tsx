"use client";

import type { CSSProperties, ReactNode } from "react";
import { type UniverseHubPluginId, UNIVERSE_HUB_SHELL_ID } from "@/lib/universeHubPluginsV2";
import { UniverseHubComplianceFooter } from "@/components/shell/UniverseHubComplianceFooter";
import { UniverseHubSiteHeader } from "@/components/shell/UniverseHubSiteHeader";
import { HubEvidenceInspectorV3 } from "@/components/shell/HubEvidenceInspectorV3";
import {
  HubInspectorResizeHandleV3,
  useHubInspectorWidthV3,
} from "@/components/shell/HubInspectorResizeHandleV3";
import { UniverseSidebarV2 } from "@/components/shell/UniverseSidebarV2";
import { useHubSidebarCollapsedV1 } from "@/hooks/useHubSidebarCollapsedV1";

export type UnifiedUniverseShellV2Props = {
  children: ReactNode;
  activePluginId?: UniverseHubPluginId;
  showInspector?: boolean;
  hubLightChrome?: boolean;
  discoverMinimal?: boolean;
  iconRail?: boolean;
};

export function UnifiedUniverseShellV2({
  children,
  activePluginId,
  showInspector = false,
  hubLightChrome = false,
  discoverMinimal = false,
  iconRail = false,
}: UnifiedUniverseShellV2Props) {
  const { width: inspectorWidth, persistWidth } = useHubInspectorWidthV3();
  const { collapsed: sidebarCollapsed, toggle: toggleSidebar } = useHubSidebarCollapsedV1(true);
  const iconRailActive = hubLightChrome && sidebarCollapsed;
  const discoverV3 = discoverMinimal && showInspector;

  const shellClass = [
    "universe-hub-shell-v2",
    showInspector ? "universe-hub-shell-v3" : "",
    hubLightChrome ? "universe-hub-shell-v2--light-chrome" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const pageClass = [
    "universe-hub-page",
    hubLightChrome ? "universe-hub-page--light-chrome" : "",
    discoverV3 ? "universe-hub-page--discover-v3" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const sidebarColumn = iconRailActive ? "4.5rem" : "minmax(200px, 240px)";

  const shellGridStyle: CSSProperties | undefined = showInspector
    ? {
        gridTemplateColumns: hubLightChrome
          ? `${sidebarColumn} minmax(0, 1fr) ${inspectorWidth}px`
          : `minmax(200px, 240px) minmax(0, 1fr) ${inspectorWidth}px`,
      }
    : hubLightChrome
      ? { gridTemplateColumns: `${sidebarColumn} minmax(0, 1fr)` }
      : undefined;

  return (
    <div className={pageClass} data-shell-id={UNIVERSE_HUB_SHELL_ID}>
      {hubLightChrome ? null : <UniverseHubSiteHeader />}
      <div className={shellClass} style={shellGridStyle}>
        <UniverseSidebarV2
          activeId={activePluginId}
          iconRail={hubLightChrome ? iconRailActive : iconRail}
          collapsed={sidebarCollapsed}
          onToggleCollapse={hubLightChrome ? toggleSidebar : undefined}
        />
        <div
          className={[
            "universe-hub-main",
            showInspector ? "universe-hub-main-v3" : "",
            discoverMinimal ? "universe-hub-main--discover-minimal" : "",
            hubLightChrome && !discoverMinimal ? "universe-hub-main--hub-spoke" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {children}
          {hubLightChrome ? null : <UniverseHubComplianceFooter />}
        </div>
        {showInspector ? (
          <aside
            className="universe-hub-inspector-v3 universe-hub-inspector-v3--resizable"
            aria-label="Observation inspector"
          >
            <HubInspectorResizeHandleV3
              currentWidth={inspectorWidth}
              onResize={persistWidth}
            />
            <HubEvidenceInspectorV3 />
          </aside>
        ) : null}
      </div>
    </div>
  );
}
