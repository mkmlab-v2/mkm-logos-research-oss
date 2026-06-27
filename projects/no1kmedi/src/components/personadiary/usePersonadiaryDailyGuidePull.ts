"use client";

import { useCallback, useState } from "react";
import { personadiaryCopy } from "@/content/personadiaryCopy";
import type { DailyGuidePackage } from "@/lib/personadiaryDailyGuide";

const DEFAULT_PROFILE =
  (typeof process !== "undefined" &&
    process.env.NEXT_PUBLIC_PERSONADIARY_PROFILE_ID?.trim()) ||
  "commander";

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

async function fetchGuideOnce(profileId: string): Promise<DailyGuidePackage> {
  const q = new URLSearchParams({ profile_id: profileId });
  const res = await fetch(`${personadiaryCopy.dailyGuide.apiPath}?${q}`, {
    cache: "no-store",
  });
  const data = await res.json();
  if (!res.ok || !data?.ok || !isValidPackage(data.package)) {
    const fallback = await loadStaticPackage(profileId);
    if (fallback) return fallback;
    throw new Error(String(data?.error || "load_failed"));
  }
  return data.package as DailyGuidePackage;
}

/** Pull-only daily guide — no network until `pull()` is called. */
export function usePersonadiaryDailyGuidePull(profileId: string = DEFAULT_PROFILE) {
  const [pulled, setPulled] = useState(false);
  const [pkg, setPkg] = useState<DailyGuidePackage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pull = useCallback(async () => {
    setPulled(true);
    setLoading(true);
    setError(null);
    try {
      const loaded = await fetchGuideOnce(profileId);
      setPkg(loaded);
    } catch {
      setError("network_error");
      setPkg(null);
    } finally {
      setLoading(false);
    }
  }, [profileId]);

  return { pulled, pull, pkg, loading, error, profileId };
}
