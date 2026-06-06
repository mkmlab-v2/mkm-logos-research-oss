import type { NextRequest } from "next/server";

export function clinicianDevUnlock(): boolean {
  const v = (process.env.KM_CLINICIAN_DEV_UNLOCK || "").trim().toLowerCase();
  if (v === "1" || v === "true" || v === "yes" || v === "on") return true;
  if (process.env.NODE_ENV === "development") return true;
  return false;
}

function clinicianProAllowlist(): Set<string> {
  const raw = process.env.KM_CLINICIAN_PRO_EMAIL_ALLOWLIST || "";
  return new Set(
    raw
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean),
  );
}

/** Server routes: chat + structured CDSS + workspace Python chains. */
export function clinicianProUnlocked(request?: NextRequest): boolean {
  if (clinicianDevUnlock()) return true;
  const email = (request?.nextUrl.searchParams.get("email") || "").trim().toLowerCase();
  if (email && clinicianProAllowlist().has(email)) return true;
  return false;
}
