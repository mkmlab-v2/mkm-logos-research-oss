"use client";

import { useEffect } from "react";
import { detectPersonadiaryRuntime } from "@/lib/personadiaryNativeBridgeHypoV1";

/** Ops /ops edge-to-edge paint + safe-area class hooks (PWA + Capacitor WebView). */
export function PersonadiaryOpsEdgeBridge() {
  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    html.classList.add("pd-ops-edge-root");
    body.classList.add("pd-ops-edge-body");
    if (detectPersonadiaryRuntime() === "capacitor_webview") {
      html.classList.add("pd-capacitor-native");
    }

    const syncInsetFlag = () => {
      const top = getComputedStyle(html).getPropertyValue("--safe-area-inset-top").trim();
      const bottom = getComputedStyle(html).getPropertyValue("--safe-area-inset-bottom").trim();
      if (
        (top && top !== "0px") ||
        (bottom && bottom !== "0px") ||
        html.dataset.pdSafeInsets === "native"
      ) {
        html.dataset.pdSafeInsets = html.dataset.pdSafeInsets || "css";
      }
    };

    syncInsetFlag();
    const timer = window.setInterval(syncInsetFlag, 1200);
    const stop = window.setTimeout(() => window.clearInterval(timer), 4000);

    return () => {
      window.clearInterval(timer);
      window.clearTimeout(stop);
      html.classList.remove("pd-ops-edge-root", "pd-capacitor-native");
      body.classList.remove("pd-ops-edge-body");
      delete html.dataset.pdSafeInsets;
    };
  }, []);

  return (
    <p className="pd-android-edge-insets-v1" hidden data-contract="android_edge_insets_p1_v1">
      pd-android-edge-insets-v1 · native WindowInsets → --safe-area-inset-* · pd-ops-edge-body
    </p>
  );
}
