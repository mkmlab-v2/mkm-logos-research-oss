import { NextRequest, NextResponse } from "next/server";

import { GET as billingIntentGet } from "@/app/api/logos-research/billing/intent/route";
import { POST as payappCreatePost } from "@/app/api/payment/payapp/create/route";
import { LOGOS_BILLING_EMAIL_COOKIE } from "@/lib/logosInquiryPayappAccessV1";
import { isLogosInquiryPaymentEnabled } from "@/lib/logosInquiryBetaV1";

export const runtime = "nodejs";

/** Server-side Pro checkout — keys never sent to browser (G12 inject via server env on prod). */
export async function POST(request: NextRequest) {
  if (!isLogosInquiryPaymentEnabled()) {
    return NextResponse.json(
      {
        success: false,
        error: "payment_deferred_post_oss_verification",
        note_ko: "결제는 OSS 공개·검증 후 연결됩니다. 베타는 무료 쿼터를 이용해 주세요.",
        feedback_issues_url: "https://github.com/mkmlab-v2/mkm-logos-research-oss/issues",
      },
      { status: 403 },
    );
  }
  try {
    const body = (await request.json().catch(() => ({}))) as { email?: string };
    const email = (body.email || "").trim().toLowerCase();
    if (!email || !email.includes("@")) {
      return NextResponse.json({ success: false, error: "valid email required" }, { status: 400 });
    }

    const intentRes = await billingIntentGet(
      new NextRequest(new URL("/api/logos-research/billing/intent?sku=pro", request.nextUrl.origin)),
    );
    const intent = (await intentRes.json()) as {
      plan_code?: string;
      product_name_ko?: string;
      amount_krw?: number;
      return_url?: string;
      send_gate?: string;
      g12_human_inject?: boolean;
    };

    const payappKey =
      process.env.PAYAPP_KEY?.trim() ||
      process.env.PAYAPP_KEY_DRY_RUN?.trim() ||
      "dry_run_key";
    const payappValue =
      process.env.PAYAPP_VALUE?.trim() ||
      process.env.PAYAPP_VALUE_DRY_RUN?.trim() ||
      "dry_run_value";

    const usingDryRun = payappKey === "dry_run_key" || payappValue === "dry_run_value";

    const createRes = await payappCreatePost(
      new NextRequest(new URL("/api/payment/payapp/create", request.nextUrl.origin), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          payapp_key: payappKey,
          payapp_value: payappValue,
          email,
          plan_code: intent.plan_code || "logos_inquiry_pro_v1",
          product_name: intent.product_name_ko || "Logos Inquiry Pro",
          amount: intent.amount_krw || 39000,
          return_url: intent.return_url || `${request.nextUrl.origin}/logos-research/ask?paid=1`,
        }),
      }),
    );
    const created = (await createRes.json()) as {
      success?: boolean;
      order_id?: string;
      redirect_url?: string;
      error?: string;
    };

    if (!createRes.ok || !created.success) {
      return NextResponse.json(
        {
          success: false,
          error: created.error || "checkout_create_failed",
          g12_human_inject: intent.g12_human_inject ?? true,
        },
        { status: createRes.status },
      );
    }

    const response = NextResponse.json({
      success: true,
      schema: "logos_inquiry_billing_checkout_v1",
      order_id: created.order_id,
      redirect_url: created.redirect_url,
      send_gate: intent.send_gate || "HOLD",
      dry_run_keys: usingDryRun,
      prod_keys_in_use: !usingDryRun,
      note_ko: usingDryRun
        ? "연구 모드 — dry_run 키로 주문 생성만 검증합니다."
        : "PayApp 결제 페이지로 이동합니다.",
    });
    response.cookies.set({
      name: LOGOS_BILLING_EMAIL_COOKIE,
      value: email,
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
    });
    return response;
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "checkout_failed";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
