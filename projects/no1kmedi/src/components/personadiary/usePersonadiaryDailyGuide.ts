"use client";

import {
  createContext,
  createElement,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { DailyGuideBlock } from "@/lib/personadiaryDailyGuide";

export type MomentPresetPolishBlock = {
  presets?: Record<
    string,
    {
      canonical_query?: string;
      summary_ko_polished?: string | null;
    }
  >;
  hero?: { body_ko_polished?: string | null };
};

export type DailyGuidePackage = {
  calendar_kst?: string;
  concept_ko?: string;
  ui_blocks?: DailyGuideBlock[];
  reflect_template_ko?: string;
  disclaimer_ko?: string;
  moment_preset_polish_v1?: MomentPresetPolishBlock;
};

type DailyGuideContextValue = {
  pkg: DailyGuidePackage | null;
  loading: boolean;
  error: string | null;
  profileId: string;
};

const DEFAULT_PROFILE =
  (typeof process !== "undefined" &&
    process.env.NEXT_PUBLIC_PERSONADIARY_PROFILE_ID?.trim()) ||
  "commander";

const FETCH_TIMEOUT_MS = 12_000;

const DailyGuideContext = createContext<DailyGuideContextValue | null>(null);

function isValidPackage(doc: unknown): doc is DailyGuidePackage {
  return (
    typeof doc === "object" &&
    doc !== null &&
    (doc as DailyGuidePackage).ui_blocks !== undefined
  );
}

async function loadStaticPackage(profileId: string): Promise<DailyGuidePackage | null> {
  const paths = [
    `/data/profiles/${profileId}.json`,
    "/data/personadiary_daily_response_package_v1.json",
  ];
  for (const path of paths) {
    try {
      const res = await fetch(path, { cache: "no-store" });
      if (!res.ok) continue;
      const doc = (await res.json()) as DailyGuidePackage;
      if (isValidPackage(doc)) return doc;
    } catch {
      /* try next */
    }
  }
  return null;
}

async function fetchDailyGuidePackage(
  profileId: string,
  signal: AbortSignal
): Promise<DailyGuidePackage> {
  const q = new URLSearchParams({ profile_id: profileId });
  const res = await fetch(`/api/personadiary/daily-guide?${q}`, {
    cache: "no-store",
    signal,
  });
  const data = await res.json();
  if (!res.ok || !data?.ok || !isValidPackage(data.package)) {
    const fallback = await loadStaticPackage(profileId);
    if (fallback) return fallback;
    throw new Error(String(data?.error || "load_failed"));
  }
  return data.package as DailyGuidePackage;
}

function useDailyGuideFetch(
  profileId: string,
  enabled: boolean
): DailyGuideContextValue {
  const [pkg, setPkg] = useState<DailyGuidePackage | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (!enabled) return;

    const id = ++requestId.current;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    setLoading(true);
    setError(null);

    (async () => {
      try {
        const loaded = await fetchDailyGuidePackage(profileId, controller.signal);
        if (requestId.current !== id) return;
        setPkg(loaded);
      } catch (err) {
        if (requestId.current !== id) return;
        const fallback = await loadStaticPackage(profileId);
        if (fallback) {
          setPkg(fallback);
          setError(null);
        } else {
          const message =
            err instanceof Error && err.name === "AbortError"
              ? "timeout"
              : "network_error";
          setError(message);
        }
      } finally {
        window.clearTimeout(timer);
        if (requestId.current === id) setLoading(false);
      }
    })();

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [profileId, enabled]);

  return { pkg, loading: enabled ? loading : false, error, profileId };
}

export function PersonadiaryDailyGuideProvider({
  children,
  profileId = DEFAULT_PROFILE,
  packageOverride = null,
}: {
  children: ReactNode;
  profileId?: string;
  /** When set, skip auto-fetch (Pull-only ops). */
  packageOverride?: DailyGuidePackage | null;
}) {
  const fetched = useDailyGuideFetch(profileId, !packageOverride);
  const value = useMemo(() => {
    if (packageOverride) {
      return {
        pkg: packageOverride,
        loading: false,
        error: null,
        profileId,
      };
    }
    return fetched;
  }, [packageOverride, fetched, profileId]);
  return createElement(DailyGuideContext.Provider, { value }, children);
}

export function usePersonadiaryDailyGuide(profileId: string = DEFAULT_PROFILE) {
  const ctx = useContext(DailyGuideContext);
  const standalone = useDailyGuideFetch(profileId, !ctx);

  if (ctx) {
    if (ctx.profileId !== profileId) {
      return { pkg: null, loading: true, error: null, profileId };
    }
    return ctx;
  }

  return standalone;
}

export function formatReflectFromGuide(
  template: string | undefined,
  userText: string
): string {
  const snippet =
    userText.trim().length > 120 ? `${userText.trim().slice(0, 120)}…` : userText.trim();
  if (template && template.includes("{user}")) {
    return template.replace("{user}", snippet);
  }
  return `오늘 당신이 남긴 마음: "${snippet}" — 구슬은 가이드형 성찰만 비춥니다.`;
}
