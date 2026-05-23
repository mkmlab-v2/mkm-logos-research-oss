"use client";

import { useEffect, useState } from "react";

export type DailyGuideBlock = {
  type: string;
  title_ko: string;
  body_ko?: string;
  ref?: string;
  badge_ko?: string;
};

export type DailyGuidePackage = {
  calendar_kst?: string;
  concept_ko?: string;
  ui_blocks?: DailyGuideBlock[];
  reflect_template_ko?: string;
  disclaimer_ko?: string;
};

const DEFAULT_PROFILE =
  (typeof process !== "undefined" &&
    process.env.NEXT_PUBLIC_PERSONADIARY_PROFILE_ID?.trim()) ||
  "commander";

export function usePersonadiaryDailyGuide(profileId: string = DEFAULT_PROFILE) {
  const [pkg, setPkg] = useState<DailyGuidePackage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const q = new URLSearchParams({ profile_id: profileId });
        const res = await fetch(`/api/personadiary/daily-guide?${q}`, {
          cache: "no-store",
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          if (!cancelled) setError(data.error || "load_failed");
          return;
        }
        if (!cancelled) setPkg(data.package as DailyGuidePackage);
      } catch {
        if (!cancelled) setError("network_error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  return { pkg, loading, error, profileId };
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
