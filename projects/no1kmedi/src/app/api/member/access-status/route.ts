import { NextRequest, NextResponse } from "next/server";
import { getPayments, getVerifications } from "../../payment/payapp/_store";

export const runtime = "nodejs";

function clinicianProAllowlist(): Set<string> {
  const raw = process.env.KM_CLINICIAN_PRO_EMAIL_ALLOWLIST || "";
  return new Set(
    raw
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean),
  );
}

export async function GET(request: NextRequest) {
  try {
    const email = (request.nextUrl.searchParams.get("email") || "").trim().toLowerCase();
    if (!email) {
      return NextResponse.json({ success: false, error: "email is required" }, { status: 400 });
    }

    if (clinicianProAllowlist().has(email)) {
      return NextResponse.json({
        success: true,
        email,
        payment_status: "allowlist",
        verification_status: "allowlist",
        can_use_pro_clinical_assist: true,
        pro_clinical_features_unlocked: true,
        access_source: "km_clinician_pro_email_allowlist",
      });
    }

    const [payments, verifications] = await Promise.all([getPayments(), getVerifications()]);
    const payment = payments.find((x) => x.email.toLowerCase() === email);
    const verification = verifications.find((x) => x.email.toLowerCase() === email);

    const paymentStatus = payment?.state || "none";
    const verificationStatus = verification?.status || "not_submitted";
    const unlocked = paymentStatus === "paid" && verificationStatus === "approved";

    return NextResponse.json({
      success: true,
      email,
      payment_status: paymentStatus,
      verification_status: verificationStatus,
      can_use_pro_clinical_assist: unlocked,
      pro_clinical_features_unlocked: unlocked,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "access status failed" },
      { status: 500 }
    );
  }
}
