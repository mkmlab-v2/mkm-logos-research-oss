import type { LogosStudioAudienceMode } from "@/lib/logosStudioAudienceModeV1";

export const LOGOS_STUDIO_ONBOARDING_STORAGE_KEY = "logos_studio_onboarding_v1";

export type LogosStudioOnboardingTopic = {
  id: string;
  label_ko: string;
  preset_id: string;
  slot_label_ko?: string;
};

/** B2B demo onboarding — 2-step topic picks (maps to preset + slot filter). */
export const LOGOS_STUDIO_ONBOARDING_TOPICS: LogosStudioOnboardingTopic[] = [
  {
    id: "job",
    label_ko: "욥기 · 고난과 의",
    preset_id: "job_job_suffering_reason",
    slot_label_ko: "욥기·고난 spine",
  },
  {
    id: "isaiah",
    label_ko: "이사야 · 부르심·임manuel",
    preset_id: "isaiah_youtube_spine_v1",
    slot_label_ko: "이사야·유튜브 spine",
  },
  {
    id: "nephilim",
    label_ko: "네피림 · 타락 천사 전통",
    preset_id: "bigset_topic_nephilim",
    slot_label_ko: "BigSet 주제",
  },
  {
    id: "era",
    label_ko: "시대·레짐 (exodus / gospel)",
    preset_id: "era_gospel_logos_incarnate",
    slot_label_ko: "시대(era)",
  },
];

export type LogosStudioOnboardingResult = {
  audienceMode: LogosStudioAudienceMode;
  topic: LogosStudioOnboardingTopic;
};

export function shouldShowLogosStudioOnboarding(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(LOGOS_STUDIO_ONBOARDING_STORAGE_KEY) !== "1";
  } catch {
    return false;
  }
}

export function markLogosStudioOnboardingComplete(): void {
  try {
    window.sessionStorage.setItem(LOGOS_STUDIO_ONBOARDING_STORAGE_KEY, "1");
  } catch {
    /* best effort */
  }
}
