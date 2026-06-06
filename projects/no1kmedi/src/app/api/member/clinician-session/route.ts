import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

function truthyEnv(name: string): boolean {
  const v = (process.env[name] || "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

function clinicianDevUnlock(): boolean {
  if (truthyEnv("KM_CLINICIAN_DEV_UNLOCK")) return true;
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

/** Session bootstrap: dev unlock, optional email check (no payment required in dev). */
export async function GET(request: NextRequest) {
  try {
    const devUnlock = clinicianDevUnlock();
    const email = (request.nextUrl.searchParams.get("email") || "").trim().toLowerCase();

    if (devUnlock) {
      return NextResponse.json({
        success: true,
        dev_unlock: true,
        can_use_chat: true,
        can_use_pro_clinical_assist: true,
        pro_clinical_features_unlocked: true,
        access_source: "km_clinician_dev_unlock",
        email: email || undefined,
      });
    }

    if (!email) {
      return NextResponse.json({
        success: true,
        dev_unlock: false,
        can_use_chat: false,
        can_use_pro_clinical_assist: false,
        access_source: "email_required",
      });
    }

    if (clinicianProAllowlist().has(email)) {
      return NextResponse.json({
        success: true,
        email,
        dev_unlock: false,
        can_use_chat: true,
        can_use_pro_clinical_assist: true,
        pro_clinical_features_unlocked: true,
        payment_status: "allowlist",
        verification_status: "allowlist",
        access_source: "km_clinician_pro_email_allowlist",
      });
    }

    const { getPayments, getVerifications } = await import("../../payment/payapp/_store");
    const [payments, verifications] = await Promise.all([getPayments(), getVerifications()]);
    const payment = payments.find((x) => x.email.toLowerCase() === email);
    const verification = verifications.find((x) => x.email.toLowerCase() === email);
    const paymentStatus = payment?.state || "none";
    const verificationStatus = verification?.status || "not_submitted";
    const unlocked = paymentStatus === "paid" && verificationStatus === "approved";

    return NextResponse.json({
      success: true,
      email,
      dev_unlock: false,
      can_use_chat: unlocked,
      can_use_pro_clinical_assist: unlocked,
      pro_clinical_features_unlocked: unlocked,
      payment_status: paymentStatus,
      verification_status: verificationStatus,
      access_source: unlocked ? "payapp_verified" : "payapp_locked",
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "clinician_session_failed";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
