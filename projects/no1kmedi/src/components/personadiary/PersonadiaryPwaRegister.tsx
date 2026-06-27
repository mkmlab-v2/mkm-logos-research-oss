"use client";

import { useEffect } from "react";

/** Registers minimal PWA service worker on personadiary ops surfaces only. */
export function PersonadiaryPwaRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    const host = window.location.hostname.toLowerCase();
    const isLocalDev = host === "localhost" || host === "127.0.0.1";

    if (isLocalDev) {
      void navigator.serviceWorker.getRegistrations().then((regs) => {
        for (const reg of regs) void reg.unregister();
      });
      return;
    }

    const path = "/personadiary/sw.js";
    const onPersonadiaryHost = host === "personadiary.com" || host.endsWith(".personadiary.com");
    const scope = onPersonadiaryHost ? "/" : "/personadiary/";
    navigator.serviceWorker.register(path, { scope }).catch(() => {
      /* optional installability; ignore failures in preview */
    });
  }, []);
  return null;
}
