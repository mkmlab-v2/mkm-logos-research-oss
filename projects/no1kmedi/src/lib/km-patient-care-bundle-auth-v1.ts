/**
 * Optional token guard for patient-care-bundle-from-cds.
 * When KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN=1, same-origin clinician UI may call without x-api-token.
 */

import type { NextRequest } from "next/server";

export function isPatientCareBundleTokenRequired(request: NextRequest): boolean {
  const guard = process.env.KM_PATIENT_CARE_BUNDLE_TOKEN?.trim();
  if (!guard) return false;
  if (process.env.KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN?.trim() === "1" && isSameOriginClinicianRequest(request)) {
    return false;
  }
  return true;
}

export function isPatientCareBundleTokenValid(request: NextRequest): boolean {
  const guard = process.env.KM_PATIENT_CARE_BUNDLE_TOKEN?.trim();
  if (!guard) return true;
  const token = request.headers.get("x-api-token")?.trim();
  return Boolean(token && token === guard);
}

function isSameOriginClinicianRequest(request: NextRequest): boolean {
  const site = request.headers.get("sec-fetch-site");
  if (site === "same-origin") return true;
  const referer = request.headers.get("referer") || "";
  try {
    const url = new URL(referer);
    if (url.pathname.startsWith("/clinician")) return true;
  } catch {
    // ignore bad referer
  }
  const origin = request.headers.get("origin");
  if (origin && origin === request.nextUrl.origin) return true;
  return false;
}
