/**
 * Global birth input contract (mkmlife / saju_birth_resolver_v1 parity):
 * prefer `birth_instant_utc` (ISO with Z or offset) + `iana_tz` for DST-safe resolution.
 * Legacy `birth_datetime` string remains for older integrations.
 */

export function looksLikeIsoInstant(s: string): boolean {
  const t = s.trim();
  if (t.length < 10) return false;
  if (!/^\d{4}-\d{2}-\d{2}[T ]\d/.test(t)) return false;
  return (
    /(?:\.\d+)?[zZ]$/.test(t) || /[+-]\d{2}:\d{2}$/.test(t) || /[+-]\d{4}$/.test(t)
  );
}

export function validateLaneABirth(profile: {
  birth_datetime?: string;
  birth_instant_utc?: string;
  iana_tz?: string;
}): string | null {
  const utc = profile.birth_instant_utc?.trim();
  const tz = profile.iana_tz?.trim();
  const legacy = profile.birth_datetime?.trim();
  if (utc && tz) {
    if (!looksLikeIsoInstant(utc)) return "invalid_birth_instant_utc";
    return null;
  }
  if (utc && !tz) return "missing_iana_tz";
  if (tz && !utc) return "missing_birth_instant_utc";
  if (legacy) return null;
  return "missing_birth_inputs";
}
