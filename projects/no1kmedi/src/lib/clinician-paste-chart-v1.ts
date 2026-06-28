/**
 * Client-safe Paste Chart helpers (no node:fs).
 */

export { inferSasangCandidateFromLabel } from "@/lib/clinician-sasang-infer-v1";

export function birthInstantToClinicBirthFields(
  birthInstantUtc: string,
  ianaTz: string,
  birthTimeKnown = false,
): { birthdate: string; birth_time?: string; birth_time_known: boolean } | null {
  const d = new Date(birthInstantUtc);
  if (Number.isNaN(d.getTime())) return null;
  const tz = ianaTz.trim() || "Asia/Seoul";
  const birthdate = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
  if (!birthdate) return null;

  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(d);
  const hh = parts.find((p) => p.type === "hour")?.value;
  const mm = parts.find((p) => p.type === "minute")?.value;
  const birth_time = hh && mm ? `${hh}:${mm}` : undefined;
  const known = birthTimeKnown && Boolean(birth_time);

  return {
    birthdate,
    birth_time: known ? birth_time : undefined,
    birth_time_known: known,
  };
}
