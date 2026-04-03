import { NextRequest, NextResponse } from "next/server";
import { getPayments } from "../_store";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    const email = (request.nextUrl.searchParams.get("email") || "").trim().toLowerCase();
    const orderId = (request.nextUrl.searchParams.get("order_id") || "").trim();
    const rows = await getPayments();

    const target = rows.find((x) =>
      orderId ? x.order_id === orderId : email ? x.email.toLowerCase() === email : false
    );

    if (!target) {
      return NextResponse.json({ success: false, error: "payment not found" }, { status: 404 });
    }

    return NextResponse.json({
      success: true,
      order_id: target.order_id,
      email: target.email,
      plan_code: target.plan_code,
      payment_status: target.state,
      updated_at: target.updated_at,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "status lookup failed" },
      { status: 500 }
    );
  }
}
