import type { NextRequest } from "next/server";
import { getPayments, getVerifications } from "@/app/api/payment/payapp/_store";

export function clinicianDevUnlock(): boolean {
  const v = (process.env.KM_CLINICIAN_DEV_UNLOCK || "").trim().toLowerCase();
  if (v === "1" || v === "true" || v === "yes" || v === "on") return true;
  if (process.env.NODE_ENV === "development") return true;
  return false;
}

export function clinicianProEnforceGate(): boolean {
  const v = (process.env.KM_CLINICIAN_ENFORCE_PRO_GATE || "").trim().toLowerCase();
  if (v === "0" || v === "false" || v === "no" || v === "off") return false;
  if (v === "1" || v === "true" || v === "yes" || v === "on") return true;
  return process.env.NODE_ENV === "production";
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

export type ClinicianProAccessResult = {
  unlocked: boolean;
  email: string;
  access_source: string;
  payment_status?: string;
  verification_status?: string;
};

export async function resolveClinicianProAccess(emailRaw: string): Promise<ClinicianProAccessResult> {
  const email = emailRaw.trim().toLowerCase();
  if (!email) {
    return { unlocked: false, email: "", access_source: "missing_email" };
  }
  if (clinicianDevUnlock()) {
    return { unlocked: true, email, access_source: "dev_unlock" };
  }
  if (clinicianProAllowlist().has(email)) {
    return {
      unlocked: true,
      email,
      access_source: "km_clinician_pro_email_allowlist",
      payment_status: "allowlist",
      verification_status: "allowlist",
    };
  }
  const [payments, verifications] = await Promise.all([getPayments(), getVerifications()]);
  const payment = payments.find((x) => x.email.toLowerCase() === email);
  const verification = verifications.find((x) => x.email.toLowerCase() === email);
  const paymentStatus = payment?.state || "none";
  const verificationStatus = verification?.status || "not_submitted";
  const unlocked = paymentStatus === "paid" && verificationStatus === "approved";
  return {
    unlocked,
    email,
    access_source: unlocked ? "payapp_paid_verified" : "payapp_incomplete",
    payment_status: paymentStatus,
    verification_status: verificationStatus,
  };
}

export function clinicianEmailFromRequest(request: NextRequest): string {
  const header = (request.headers?.get?.("x-clinician-email") || "").trim().toLowerCase();
  if (header) return header;
  try {
    return (request.nextUrl?.searchParams.get("email") || "").trim().toLowerCase();
  } catch {
    return "";
  }
}

/** Server routes: chat + structured CDSS + workspace Python chains. */
export function clinicianProUnlocked(request?: NextRequest): boolean {
  if (clinicianDevUnlock()) return true;
  const email = clinicianEmailFromRequest(request ?? ({} as NextRequest));
  if (email && clinicianProAllowlist().has(email)) return true;
  return false;
}

export async function clinicianProUnlockedAsync(request?: NextRequest): Promise<ClinicianProAccessResult> {
  if (clinicianDevUnlock()) {
    return { unlocked: true, email: "", access_source: "dev_unlock" };
  }
  const email = clinicianEmailFromRequest(request ?? ({} as NextRequest));
  if (!email) {
    return { unlocked: false, email: "", access_source: "missing_email" };
  }
  return resolveClinicianProAccess(email);
}
