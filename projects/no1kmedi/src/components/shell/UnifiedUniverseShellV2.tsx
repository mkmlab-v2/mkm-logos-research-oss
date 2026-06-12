"use client";

import type { ReactNode } from "react";
import { type UniverseHubPluginId, UNIVERSE_HUB_SHELL_ID } from "@/lib/universeHubPluginsV2";
import { UniverseHubComplianceFooter } from "@/components/shell/UniverseHubComplianceFooter";
import { UniverseHubSiteHeader } from "@/components/shell/UniverseHubSiteHeader";
import { HubEvidenceInspectorV3 } from "@/components/shell/HubEvidenceInspectorV3";
import { UniverseSidebarV2 } from "@/components/shell/UniverseSidebarV2";

export type UnifiedUniverseShellV2Props = {
  children: ReactNode;
  activePluginId?: UniverseHubPluginId;
  showInspector?: boolean;
  discoverMinimal?: boolean;
};

export function UnifiedUniverseShellV2({
  children,
  activePluginId,
  showInspector = false,
  discoverMinimal = false,
}: UnifiedUniverseShellV2Props) {
  const shellClass = [
    "universe-hub-shell-v2",
    showInspector ? "universe-hub-shell-v3" : "",
    discoverMinimal ? "universe-hub-shell-v2--discover-minimal" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const pageClass = [
    "universe-hub-page",
    discoverMinimal ? "universe-hub-page--discover-minimal" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={pageClass} data-shell-id={UNIVERSE_HUB_SHELL_ID}>
      {discoverMinimal ? null : <UniverseHubSiteHeader />}
      <div className={shellClass}>
        <UniverseSidebarV2 activeId={activePluginId} iconRail={discoverMinimal} />
        <div
          className={[
            "universe-hub-main",
            showInspector ? "universe-hub-main-v3" : "",
            discoverMinimal ? "universe-hub-main--discover-minimal" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {children}
          {discoverMinimal ? null : <UniverseHubComplianceFooter />}
        </div>
        {showInspector ? (
          <aside className="universe-hub-inspector-v3" aria-label="Observation inspector">
            <HubEvidenceInspectorV3 />
          </aside>
        ) : null}
      </div>
    </div>
  );
}
