"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { HubDiscoverLayoutProvider } from "@/components/shell/HubDiscoverLayoutContext";
import { UnifiedUniverseShellV2 } from "@/components/shell/UnifiedUniverseShellV2";
import {
  isHubDiscoverMinimalMode,
  isHubLightChrome,
} from "@/lib/universeHubDiscoverMinimalV1";
import { shouldShowHubInspectorV3 } from "@/lib/universeHubInspectorV3";
import { activePluginIdFromPath } from "@/lib/universeHubPathActivePlugin";

type Props = {
  children: ReactNode;
};

export function HubShellClient({ children }: Props) {
  const pathname = usePathname() ?? "";
  const activePluginId = activePluginIdFromPath(pathname);
  const hubLightChrome = isHubLightChrome(pathname);
  const discoverMinimal = isHubDiscoverMinimalMode(pathname);
  const showInspector = shouldShowHubInspectorV3(pathname);

  return (
    <HubDiscoverLayoutProvider discoverMinimal={discoverMinimal}>
      <UnifiedUniverseShellV2
        activePluginId={activePluginId}
        showInspector={showInspector}
        hubLightChrome={hubLightChrome}
        discoverMinimal={discoverMinimal}
        iconRail={hubLightChrome}
      >
        {children}
      </UnifiedUniverseShellV2>
    </HubDiscoverLayoutProvider>
  );
}
