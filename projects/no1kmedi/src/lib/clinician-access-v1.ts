/** Clinician workspace access helpers (client-safe flags from API only). */

export const CLINICIAN_ACCESS_EMAIL_KEY = "mkm_clinician_access_email_v1";

export type ClinicianSessionResponse = {
  success: boolean;
  dev_unlock?: boolean;
  can_use_chat?: boolean;
  can_use_pro_clinical_assist?: boolean;
  access_source?: string;
  error?: string;
};

export function loadSavedClinicianEmail(): string {
  if (typeof window === "undefined") return "";
  try {
    return (window.localStorage.getItem(CLINICIAN_ACCESS_EMAIL_KEY) || "").trim();
  } catch {
    return "";
  }
}

export function saveClinicianEmail(email: string): void {
  if (typeof window === "undefined") return;
  try {
    const v = email.trim().toLowerCase();
    if (v) window.localStorage.setItem(CLINICIAN_ACCESS_EMAIL_KEY, v);
  } catch {
    /* quota */
  }
}
