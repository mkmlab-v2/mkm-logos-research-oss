import type { UniverseHubPluginId } from "@/lib/universeHubPluginsV2";

/** Map pathname → sidebar active plugin (deterministic, no LLM). */
export function activePluginIdFromPath(pathname: string): UniverseHubPluginId | undefined {
  const path = pathname.replace(/\/$/, "") || "/hub";
  if (path === "/hub") return "discover";
  if (path.startsWith("/hub/customize")) return "governed_customization";
  if (path.startsWith("/hub/oracle")) return "oracle_observatory";
  if (path.startsWith("/hub/logos")) return "logos_observatory";
  if (path.startsWith("/hub/life")) return "mkm_life";
  if (path.startsWith("/hub/developer")) return "a_code_sandbox";
  if (path.startsWith("/hub/compression")) return "compression_sandbox";
  if (path.startsWith("/hub/reports")) return "my_reports";
  if (path.startsWith("/hub/operator")) return "operator_wtt";
  if (path.startsWith("/clinician")) return "clinician";
  return undefined;
}
