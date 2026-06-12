"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { UnifiedUniverseShellV2 } from "@/components/shell/UnifiedUniverseShellV2";
import { shouldShowHubInspectorV3 } from "@/lib/universeHubInspectorV3";
import { activePluginIdFromPath } from "@/lib/universeHubPathActivePlugin";

type Props = {
  children: ReactNode;
};

export function HubShellClient({ children }: Props) {
  const pathname = usePathname() ?? "";
  const activePluginId = activePluginIdFromPath(pathname);

  const showInspector = shouldShowHubInspectorV3(pathname);

  return (
    <UnifiedUniverseShellV2 activePluginId={activePluginId} showInspector={showInspector}>
      {children}
    </UnifiedUniverseShellV2>
  );
}
