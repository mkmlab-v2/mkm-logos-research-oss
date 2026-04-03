import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { getPayments, savePayments } from "../_store";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      payapp_key,
      payapp_value,
      email,
      plan_code,
      product_name,
      return_url,
      amount,
    } = body ?? {};

    if (!payapp_key || !payapp_value || !email || !plan_code) {
      return NextResponse.json(
        { success: false, error: "payapp_key, payapp_value, email, plan_code are required." },
        { status: 400 }
      );
    }

    const orderId = `mkm_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
    const token = crypto.randomBytes(8).toString("hex");
    const now = new Date().toISOString();

    const rows = await getPayments();
    rows.unshift({
      order_id: orderId,
      email,
      plan_code,
      amount: Number(amount) || undefined,
      state: "pending",
      raw: { product_name, return_url },
      created_at: now,
      updated_at: now,
    });
    await savePayments(rows);

    // NOTE: Replace this URL with real PayApp request URL generation when provider spec is finalized.
    const redirectUrl = `https://api.payapp.kr/oapi/pay?mul_no=${encodeURIComponent(
      payapp_key
    )}&ordr_idxx=${encodeURIComponent(orderId)}&good_name=${encodeURIComponent(
      product_name || "MKM Hanui Clinical Assistant"
    )}&good_mny=${encodeURIComponent(String(amount || 39000))}&feedbackurl=${encodeURIComponent(
      `${request.nextUrl.origin}/api/payment/payapp/feedback`
    )}&return_url=${encodeURIComponent(return_url || request.nextUrl.origin)}&token=${token}`;

    return NextResponse.json({
      success: true,
      order_id: orderId,
      payment_status: "pending",
      redirect_url: redirectUrl,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error?.message || "payapp create failed" },
      { status: 500 }
    );
  }
}
