/**
 * Resolve clinic intake birthdate + optional local time → global birth contract.
 */

import { looksLikeIsoInstant } from "@/lib/global-birth-input";

export type ClinicBirthResolution = {
  birth_instant_utc: string;
  iana_tz: string;
  birth_time_known: boolean;
  birth_time_defaulted: boolean;
};

const DEFAULT_IANA_TZ = "Asia/Seoul";
const DEFAULT_LOCAL_TIME = "12:00";

/** Parse YYYY-MM-DD or YYYY.MM.DD or YYYYMMDD (8 digits). */
export function parseClinicBirthdate(raw: string): { y: number; m: number; d: number } | null {
  const t = raw.trim();
  if (!t) return null;
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(t);
  if (iso) {
    return { y: Number(iso[1]), m: Number(iso[2]), d: Number(iso[3]) };
  }
  const dot = /^(\d{4})\.(\d{1,2})\.(\d{1,2})$/.exec(t);
  if (dot) {
    return { y: Number(dot[1]), m: Number(dot[2]), d: Number(dot[3]) };
  }
  const compact = /^(\d{4})(\d{2})(\d{2})$/.exec(t);
  if (compact) {
    return { y: Number(compact[1]), m: Number(compact[2]), d: Number(compact[3]) };
  }
  return null;
}

function parseLocalTime(raw: string | undefined): { hh: number; mm: number } | null {
  const t = (raw || "").trim();
  if (!t) return null;
  const m = /^(\d{1,2}):(\d{2})$/.exec(t);
  if (!m) return null;
  const hh = Number(m[1]);
  const mm = Number(m[2]);
  if (hh < 0 || hh > 23 || mm < 0 || mm > 59) return null;
  return { hh, mm };
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/**
 * Build ISO Z from local wall clock in Asia/Seoul (+09:00, no DST since 1988).
 */
export function resolveClinicBirthInstant(input: {
  birthdate: string;
  birthTime?: string;
  birthTimeKnown?: boolean;
  ianaTz?: string;
}): ClinicBirthResolution | null {
  const parsed = parseClinicBirthdate(input.birthdate);
  if (!parsed) return null;
  const iana_tz = (input.ianaTz || DEFAULT_IANA_TZ).trim() || DEFAULT_IANA_TZ;
  const birth_time_known = input.birthTimeKnown !== false && Boolean(parseLocalTime(input.birthTime));
  const time = birth_time_known ? parseLocalTime(input.birthTime)! : parseLocalTime(DEFAULT_LOCAL_TIME)!;
  const localIso = `${parsed.y}-${pad2(parsed.m)}-${pad2(parsed.d)}T${pad2(time.hh)}:${pad2(time.mm)}:00+09:00`;
  const instant = new Date(localIso);
  if (Number.isNaN(instant.getTime())) return null;
  const birth_instant_utc = instant.toISOString();
  if (!looksLikeIsoInstant(birth_instant_utc)) return null;
  return {
    birth_instant_utc,
    iana_tz,
    birth_time_known,
    birth_time_defaulted: !birth_time_known,
  };
}

export function extractSajuLabelFromVerifyLite(myeongniLite: Record<string, unknown> | null): string | null {
  if (!myeongniLite || typeof myeongniLite !== "object") return null;
  const pillars = myeongniLite.pillars_native ?? myeongniLite.pillars ?? myeongniLite.saju_label;
  if (typeof pillars === "string" && pillars.trim()) return pillars.trim();
  if (typeof myeongniLite.saju_label === "string" && myeongniLite.saju_label.trim()) {
    return myeongniLite.saju_label.trim();
  }
  const year = myeongniLite.year_pillar ?? myeongniLite.year;
  const month = myeongniLite.month_pillar ?? myeongniLite.month;
  const day = myeongniLite.day_pillar ?? myeongniLite.day;
  const hour = myeongniLite.hour_pillar ?? myeongniLite.hour;
  if ([year, month, day, hour].every((p) => typeof p === "string" && p.trim())) {
    return [year, month, day, hour].join(" ");
  }
  return null;
}
