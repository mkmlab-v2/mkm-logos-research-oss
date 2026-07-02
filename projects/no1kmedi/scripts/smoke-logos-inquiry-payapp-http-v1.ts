/**
 * Offline PayApp E2E HTTP chain — imports Next route handlers (no dev server).
 * intent → create → feedback(paid) → status
 */
/** Wire smoke only — does not enable prod billing UI. */
process.env.LOGOS_INQUIRY_PAYMENT_ENABLED = process.env.LOGOS_INQUIRY_PAYMENT_ENABLED || "1";

import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { NextRequest } from "next/server";

import { GET as billingIntentGet } from "../src/app/api/logos-research/billing/intent/route";
import { POST as billingCheckoutPost } from "../src/app/api/logos-research/billing/checkout/route";
import { POST as payappCreatePost } from "../src/app/api/payment/payapp/create/route";
import { POST as payappFeedbackPost } from "../src/app/api/payment/payapp/feedback/route";
import { GET as payappStatusGet } from "../src/app/api/payment/payapp/status/route";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../../..");
const OUT = path.join(ROOT, "reports/logos_inquiry_payapp_http_smoke_v1_latest.json");

const BASE = "http://localhost:0";

async function readJson<T>(res: Response): Promise<T> {
  return (await res.json()) as T;
}

async function main() {
  const intentRes = await billingIntentGet(new NextRequest(`${BASE}/api/logos-research/billing/intent?sku=pro`));
  const intent = await readJson<Record<string, unknown>>(intentRes);
  if (!intentRes.ok || intent.schema !== "logos_inquiry_billing_intent_v1") {
    throw new Error(`intent_failed status=${intentRes.status}`);
  }
  if (intent.plan_code !== "logos_inquiry_pro_v1") {
    throw new Error(`unexpected plan_code ${String(intent.plan_code)}`);
  }

  const createRes = await payappCreatePost(
    new NextRequest(`${BASE}/api/payment/payapp/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        payapp_key: "dry_run_key",
        payapp_value: "dry_run_value",
        email: "logos-e2e@example.com",
        plan_code: intent.plan_code,
        product_name: intent.product_name_ko || "Logos Inquiry Pro",
        amount: intent.amount_krw || 39000,
        return_url: intent.return_url,
      }),
    }),
  );
  const created = await readJson<{ success?: boolean; order_id?: string }>(createRes);
  if (!createRes.ok || !created.success || !created.order_id) {
    throw new Error(`create_failed status=${createRes.status}`);
  }

  const feedbackRes = await payappFeedbackPost(
    new NextRequest(`${BASE}/api/payment/payapp/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_id: created.order_id,
        email: "logos-e2e@example.com",
        plan_code: "logos_inquiry_pro_v1",
        state: "paid",
      }),
    }),
  );
  const feedback = await readJson<{ success?: boolean }>(feedbackRes);
  if (!feedbackRes.ok || !feedback.success) {
    throw new Error(`feedback_failed status=${feedbackRes.status}`);
  }

  const statusRes = await payappStatusGet(
    new NextRequest(`${BASE}/api/payment/payapp/status?order_id=${encodeURIComponent(created.order_id)}`),
  );
  const status = await readJson<{ success?: boolean; payment_status?: string }>(statusRes);
  if (!statusRes.ok || !status.success || status.payment_status !== "paid") {
    throw new Error(`status_failed status=${statusRes.status} payment=${status.payment_status}`);
  }

  const checkoutRes = await billingCheckoutPost(
    new NextRequest(`${BASE}/api/logos-research/billing/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "logos-checkout@example.com" }),
    }),
  );
  const checkout = await readJson<{ success?: boolean; order_id?: string; dry_run_keys?: boolean }>(
    checkoutRes,
  );
  if (!checkoutRes.ok || !checkout.success || !checkout.order_id) {
    throw new Error(`checkout_failed status=${checkoutRes.status}`);
  }

  const report = {
    schema: "logos_inquiry_payapp_http_smoke_v1",
    ok: true,
    phase: "P0-2",
    mode: "offline_route_handlers",
    send_gate: intent.send_gate || "HOLD",
    order_id: created.order_id,
    checkout_order_id: checkout.order_id,
    dry_run_keys: checkout.dry_run_keys ?? true,
    plan_code: intent.plan_code,
    payment_status: status.payment_status,
    generated_at_utc: new Date().toISOString(),
    reproduce: "npm run smoke:logos-inquiry-payapp-http",
  };

  mkdirSync(path.dirname(OUT), { recursive: true });
  writeFileSync(OUT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ ok: true, out: OUT, order_id: created.order_id }));
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: String(err) }));
  process.exit(1);
});
