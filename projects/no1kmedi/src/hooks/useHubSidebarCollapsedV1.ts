"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "mkm_hub_sidebar_collapsed_v1";

/** Hub discover: icon rail (collapsed) vs labeled sidebar (expanded). */
export function useHubSidebarCollapsedV1(defaultCollapsed = true) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw === "0") setCollapsed(false);
      if (raw === "1") setCollapsed(true);
    } catch {
      /* localStorage unavailable */
    }
  }, []);

  const toggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const setCollapsedPersisted = useCallback((next: boolean) => {
    setCollapsed(next);
    try {
      localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, []);

  return { collapsed, toggle, setCollapsed: setCollapsedPersisted };
}
