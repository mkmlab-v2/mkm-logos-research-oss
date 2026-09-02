"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  type ReactNode,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { HubDiscoverLocale } from "@/lib/universeHubDiscoverCopyV2";

type HubLocaleContextValue = {
  locale: HubDiscoverLocale;
  setLocale: (next: HubDiscoverLocale) => void;
  toggleLocale: () => void;
};

const HubLocaleContext = createContext<HubLocaleContextValue | null>(null);

export function HubLocaleProvider({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname() ?? "/hub";
  const queryLocale = searchParams?.get("locale");
  const locale: HubDiscoverLocale = queryLocale === "en" ? "en" : "ko";

  useEffect(() => {
    document.documentElement.lang = locale === "en" ? "en" : "ko";
  }, [locale]);

  const setLocale = useCallback(
    (next: HubDiscoverLocale) => {
      const params = new URLSearchParams(searchParams?.toString() ?? "");
      if (next === "ko") {
        params.delete("locale");
      } else {
        params.set("locale", next);
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const toggleLocale = useCallback(() => {
    setLocale(locale === "ko" ? "en" : "ko");
  }, [locale, setLocale]);

  return (
    <HubLocaleContext.Provider value={{ locale, setLocale, toggleLocale }}>
      {children}
    </HubLocaleContext.Provider>
  );
}

export function useHubLocale(): HubLocaleContextValue {
  const ctx = useContext(HubLocaleContext);
  if (!ctx) {
    // Fail-open for SSR/prerender when provider not yet mounted
    return {
      locale: "ko",
      setLocale: () => undefined,
      toggleLocale: () => undefined,
    };
  }
  return ctx;
}
