import { NextRequest, NextResponse } from "next/server";

import { readFile } from "node:fs/promises";
import path from "node:path";

export const runtime = "nodejs";

type BillingIntent = {
  schema: "logos_inquiry_billing_intent_v1";
  sku: string;
  plan_code: string | null;
  product_name_ko: string | null;
  amount_krw: number | null;
  payapp_create_path: string;
  payapp_status_path: string;
  payapp_feedback_path: string;
  send_gate: string;
  prod_keys_required: boolean;
  g12_human_inject: boolean;
  server_g12_ready: boolean;
  inquiry_query_path: string;
  return_url: string;
};

async function loadContract(): Promise<Record<string, unknown>> {
  const contractPath = path.join(
    process.cwd(),
    "../../docs/final/artifacts/logos_inquiry_payapp_e2e_contract_v1_latest.json",
  );
  try {
    const raw = await readFile(contractPath, "utf8");
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return {};
  }
}

export async function GET(request: NextRequest) {
  const sku = (request.nextUrl.searchParams.get("sku") || "pro").trim().toLowerCase();
  const contract = await loadContract();
  const plans = (contract.sku_plans as Record<string, Record<string, unknown>>) || {};
  const row = plans[sku] || plans.pro || {};

  const body: BillingIntent = {
    schema: "logos_inquiry_billing_intent_v1",
    sku,
    plan_code: (row.plan_code as string) || (sku === "demo" ? null : "logos_inquiry_pro_v1"),
    product_name_ko: (row.product_name_ko as string) || null,
    amount_krw: (row.amount_krw_default as number) || null,
    payapp_create_path: "/api/payment/payapp/create",
    payapp_status_path: "/api/payment/payapp/status",
    payapp_feedback_path: "/api/payment/payapp/feedback",
    send_gate: (contract.send_gate as string) || "HOLD",
    prod_keys_required: sku !== "demo",
    g12_human_inject: true,
    server_g12_ready: Boolean(
      process.env.PAYAPP_KEY?.trim() && process.env.PAYAPP_VALUE?.trim(),
    ),
    inquiry_query_path: "/api/logos-research/query",
    return_url:
      ((contract.e2e_flow as Record<string, Record<string, string>>)?.step_2_create?.return_url_default as string) ||
      "https://logos.jema-ai.com/logos-research/ask?paid=1",
  };

  if (sku === "demo") {
    return NextResponse.json({
      ...body,
      payapp_required: false,
      note_ko: "데모 SKU — PayApp 없이 일일 쿼터.",
    });
  }

  return NextResponse.json(body, { headers: { "Cache-Control": "no-store" } });
}
