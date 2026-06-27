"use client";

import { useEffect } from "react";

const COMMERCIAL_MARKER = "pd-commercial-home-v1";
const RELOAD_KEY = "pd_commercial_bundle_reload_v1";

/** Dev-only: recover from stale HMR client chunks that replace SSR commercial home. */
export function PersonadiaryCommercialBundleGuard() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    const hasMarker = Boolean(document.querySelector(".pd-commercial-home-ssot"));
    if (hasMarker) {
      sessionStorage.removeItem(RELOAD_KEY);
      return;
    }
    if (sessionStorage.getItem(RELOAD_KEY)) return;
    sessionStorage.setItem(RELOAD_KEY, "1");
    const url = new URL(window.location.href);
    url.searchParams.set("v", `commercial-${Date.now()}`);
    window.location.replace(url.toString());
  }, []);

  return null;
}

export { COMMERCIAL_MARKER };
