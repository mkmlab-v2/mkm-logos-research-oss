import { NextRequest, NextResponse } from "next/server";
import { getPayments, getVerifications } from "../../payment/payapp/_store";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    const email = (request.nextUrl.searchParams.get("email") || "").trim().toLowerCase();
    if (!email) {
      return NextResponse.json({ success: false, error: "email is required" }, { status: 400 });
    }

    const [payments, verifications] = await Promise.all([getPayments(), getVerifications()]);
    const payment = payments.find((x) => x.email.toLowerCase() === email);
    const verification = verifications.find((x) => x.email.toLowerCase() === email);

    const paymentStatus = payment?.state || "none";
    const verificationStatus = verification?.status || "not_submitted";
    const canUseProClinicalAssist = paymentStatus === "paid" && verificationStatus === "approved";

    return NextResponse.json({
      success: true,
      email,
      payment_status: paymentStatus,
      verification_status: verificationStatus,
      can_use_pro_clinical_assist: canUseProClinicalAssist,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "access status failed" },
      { status: 500 }
    );
  }
}
