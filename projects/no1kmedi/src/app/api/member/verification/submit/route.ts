import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { getVerifications, saveVerifications } from "../../../payment/payapp/_store";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { email, clinic_name, biz_number, license_number, note } = body ?? {};
    if (!email || !clinic_name || !biz_number || !license_number) {
      return NextResponse.json(
        { success: false, error: "email, clinic_name, biz_number, license_number are required." },
        { status: 400 }
      );
    }

    const rows = await getVerifications();
    const now = new Date().toISOString();
    const id = `verify_${Date.now()}_${crypto.randomBytes(4).toString("hex")}`;
    rows.unshift({
      id,
      email: String(email).toLowerCase(),
      clinic_name,
      biz_number,
      license_number,
      note,
      status: "pending",
      created_at: now,
      updated_at: now,
    });
    await saveVerifications(rows);

    return NextResponse.json({ success: true, verification_id: id, verification_status: "pending" });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "verification submit failed" },
      { status: 500 }
    );
  }
}
