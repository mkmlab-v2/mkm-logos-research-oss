"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { UnifiedUniverseShellV2 } from "@/components/shell/UnifiedUniverseShellV2";
import { activePluginIdFromPath } from "@/lib/universeHubPathActivePlugin";

type Props = {
  children: ReactNode;
};

export function HubShellClient({ children }: Props) {
  const pathname = usePathname() ?? "";
  const activePluginId = activePluginIdFromPath(pathname);

  return <UnifiedUniverseShellV2 activePluginId={activePluginId}>{children}</UnifiedUniverseShellV2>;
}
