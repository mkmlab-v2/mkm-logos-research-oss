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
};

export function UnifiedUniverseShellV2({
  children,
  activePluginId,
  showInspector = false,
}: UnifiedUniverseShellV2Props) {
  const shellClass = showInspector
    ? "universe-hub-shell-v2 universe-hub-shell-v3"
    : "universe-hub-shell-v2";

  return (
    <div className="universe-hub-page" data-shell-id={UNIVERSE_HUB_SHELL_ID}>
      <UniverseHubSiteHeader />
      <div className={shellClass}>
        <UniverseSidebarV2 activeId={activePluginId} />
        <div className={`universe-hub-main${showInspector ? " universe-hub-main-v3" : ""}`}>
          {children}
          <UniverseHubComplianceFooter />
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
