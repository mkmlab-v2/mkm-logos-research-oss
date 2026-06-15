"use client";

import { useEffect } from "react";

/** Registers minimal PWA service worker on personadiary ops surfaces only. */
export function PersonadiaryPwaRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    const path = "/personadiary/sw.js";
    const host = window.location.hostname.toLowerCase();
    const onPersonadiaryHost = host === "personadiary.com" || host.endsWith(".personadiary.com");
    const scope = onPersonadiaryHost ? "/" : "/personadiary/";
    navigator.serviceWorker.register(path, { scope }).catch(() => {
      /* optional installability; ignore failures in preview */
    });
  }, []);
  return null;
}
