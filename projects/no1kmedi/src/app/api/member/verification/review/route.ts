import { NextRequest, NextResponse } from "next/server";
import { getVerifications, saveVerifications } from "../../../payment/payapp/_store";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { verification_id, decision, admin_token, reviewer } = body ?? {};
    if (!verification_id || !decision) {
      return NextResponse.json(
        { success: false, error: "verification_id and decision are required." },
        { status: 400 }
      );
    }

    const expected = process.env.NO1KMEDI_ADMIN_TOKEN;
    if (expected && admin_token !== expected) {
      return NextResponse.json({ success: false, error: "unauthorized" }, { status: 401 });
    }

    if (!["approved", "rejected"].includes(decision)) {
      return NextResponse.json({ success: false, error: "decision must be approved or rejected" }, { status: 400 });
    }

    const rows = await getVerifications();
    const idx = rows.findIndex((x) => x.id === verification_id);
    if (idx < 0) {
      return NextResponse.json({ success: false, error: "verification not found" }, { status: 404 });
    }

    rows[idx] = {
      ...rows[idx],
      status: decision,
      reviewed_by: reviewer || "admin",
      updated_at: new Date().toISOString(),
    };
    await saveVerifications(rows);

    return NextResponse.json({
      success: true,
      verification_id,
      verification_status: rows[idx].status,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "verification review failed" },
      { status: 500 }
    );
  }
}
