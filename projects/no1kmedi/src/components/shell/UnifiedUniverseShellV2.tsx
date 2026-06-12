import type { ReactNode } from "react";
import { type UniverseHubPluginId, UNIVERSE_HUB_SHELL_ID } from "@/lib/universeHubPluginsV2";
import { UniverseHubComplianceFooter } from "@/components/shell/UniverseHubComplianceFooter";
import { UniverseHubSiteHeader } from "@/components/shell/UniverseHubSiteHeader";
import { UniverseSidebarV2 } from "@/components/shell/UniverseSidebarV2";

export type UnifiedUniverseShellV2Props = {
  children: ReactNode;
  activePluginId?: UniverseHubPluginId;
};

export function UnifiedUniverseShellV2({ children, activePluginId }: UnifiedUniverseShellV2Props) {
  return (
    <div className="universe-hub-page" data-shell-id={UNIVERSE_HUB_SHELL_ID}>
      <UniverseHubSiteHeader />
      <div className="universe-hub-shell-v2">
        <UniverseSidebarV2 activeId={activePluginId} />
        <div className="universe-hub-main">
          {children}
          <UniverseHubComplianceFooter />
        </div>
      </div>
    </div>
  );
}
