import type { MkmFamilyRpProduct } from "@/lib/mkmFamilyAuthConfigV1";
import type { MkmFamilySessionV1 } from "@/hooks/useMkmFamilySessionV1";
import type { UniverseHubPluginId } from "@/lib/universeHubPluginsV2";

export function mkmFamilyRpProductForPlugin(
  pluginId: UniverseHubPluginId,
): MkmFamilyRpProduct | null {
  if (pluginId === "personadiary_preview") return "personadiary";
  return null;
}

export function mkmFamilyHandoffHref(product: MkmFamilyRpProduct): string {
  return `/api/mkm-family/rp/handoff?product=${product}`;
}

/** When logged in + OAuth configured, RP plugins use IdP handoff instead of bare external URL. */
export function resolveUniverseHubPluginHref(
  pluginId: UniverseHubPluginId,
  defaultHref: string,
  session: MkmFamilySessionV1 | null,
): string {
  const product = mkmFamilyRpProductForPlugin(pluginId);
  if (!product || !session?.configured || !session.authenticated) {
    return defaultHref;
  }
  return mkmFamilyHandoffHref(product);
}

export function isMkmFamilyHandoffHref(href: string): boolean {
  return href.startsWith("/api/mkm-family/rp/handoff");
}
