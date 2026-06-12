import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

/** P4: optional iframe embed — default OFF until build sets NEXT_PUBLIC_UNIVERSE_HUB_MKMLIFE_EMBED=1 */
export function isMkmlifeEmbedEnabled(): boolean {
  return process.env.NEXT_PUBLIC_UNIVERSE_HUB_MKMLIFE_EMBED === "1";
}

export type MkmlifeEmbedView = "ask-one" | "home" | "news-deck";

export function buildMkmlifeEmbedSrc(opts?: {
  prefill?: string;
  view?: MkmlifeEmbedView;
}): string {
  const override = process.env.NEXT_PUBLIC_UNIVERSE_HUB_MKMLIFE_EMBED_URL?.trim();
  const view = opts?.view ?? "ask-one";
  let base: string;
  if (override) {
    base = override;
  } else if (view === "home") {
    base = UNIVERSE_HUB_DEEP_LINKS.mkmlifeHome;
  } else if (view === "news-deck") {
    base = UNIVERSE_HUB_DEEP_LINKS.mkmlifeNewsDeck;
  } else {
    base = UNIVERSE_HUB_DEEP_LINKS.mkmlifeAskOne;
  }
  const url = new URL(base);
  url.searchParams.set("source", "jema_hub_v2");
  url.searchParams.set("embed", "1");
  if (opts?.prefill?.trim()) {
    url.searchParams.set("prefill", opts.prefill.trim());
  }
  return url.toString();
}

/** When embed is on, keep life intent inside hub shell instead of top-level navigation to mkmlife. */
export function hubLifeInternalRoute(prefill?: string): string {
  const params = new URLSearchParams({ source: "jema_hub_v2" });
  if (prefill?.trim()) {
    params.set("prefill", prefill.trim());
  }
  return `/hub/life?${params}`;
}
