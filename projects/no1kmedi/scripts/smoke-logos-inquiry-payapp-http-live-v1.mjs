/**
 * Live PayApp E2E HTTP chain against running Next dev (no redirect to payapp.kr).
 * Usage: node ./scripts/smoke-logos-inquiry-payapp-http-live-v1.mjs [--base http://localhost:3010]
 */
import { writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../../..");
const OUT = path.join(ROOT, "reports/logos_inquiry_payapp_http_live_smoke_v1_latest.json");

const base = (
  process.argv.find((a) => a.startsWith("--base="))?.slice(7) ||
  process.argv[process.argv.indexOf("--base") + 1] ||
  "http://localhost:3010"
).replace(/\/$/, "");

const testEmail = `logos-live-e2e-${Date.now()}@example.com`;

async function readJson(res) {
  return res.json();
}

async function main() {
  const intentRes = await fetch(`${base}/api/logos-research/billing/intent?sku=pro`);
  const intent = await readJson(intentRes);
  if (!intentRes.ok || intent.schema !== "logos_inquiry_billing_intent_v1") {
    throw new Error(`intent_failed status=${intentRes.status}`);
  }

  const checkoutRes = await fetch(`${base}/api/logos-research/billing/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: testEmail }),
  });
  const checkout = await readJson(checkoutRes);
  const setCookie = checkoutRes.headers.get("set-cookie") || "";
  if (!checkoutRes.ok || !checkout.success || !checkout.order_id) {
    throw new Error(`checkout_failed status=${checkoutRes.status} err=${checkout.error || ""}`);
  }
  if (!checkout.redirect_url?.includes("payapp")) {
    throw new Error("checkout_missing_redirect_url");
  }

  const feedbackRes = await fetch(`${base}/api/payment/payapp/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      order_id: checkout.order_id,
      email: testEmail,
      plan_code: intent.plan_code || "logos_inquiry_pro_v1",
      state: "paid",
    }),
  });
  const feedback = await readJson(feedbackRes);
  if (!feedbackRes.ok || !feedback.success) {
    throw new Error(`feedback_failed status=${feedbackRes.status}`);
  }

  const statusRes = await fetch(
    `${base}/api/payment/payapp/status?order_id=${encodeURIComponent(checkout.order_id)}`,
  );
  const status = await readJson(statusRes);
  if (!statusRes.ok || status.payment_status !== "paid") {
    throw new Error(`status_failed payment=${status.payment_status}`);
  }

  const queryRes = await fetch(`${base}/api/logos-research/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-logos-billing-email": testEmail,
      Cookie: setCookie,
    },
    body: JSON.stringify({
      query: "요한복음 1:1 — lemma 관점 연구 질문",
      output_format: "text_mvp_report_v1",
      domain_lane: "logos",
      intent_chip: "reports",
    }),
  });
  const queryBody = await readJson(queryRes);
  const proUnlockOk = queryRes.ok && queryBody.ok === true && Boolean(queryBody.report);

  const report = {
    schema: "logos_inquiry_payapp_http_live_smoke_v1",
    ok: proUnlockOk,
    phase: "P0-2",
    mode: "live_dev_http",
    send_gate: intent.send_gate || "HOLD",
    base,
    order_id: checkout.order_id,
    dry_run_keys: checkout.dry_run_keys ?? null,
    prod_keys_in_use: checkout.prod_keys_in_use ?? false,
    g12_keys_on_server: checkout.prod_keys_in_use === true,
    pro_unlock_via_payapp: proUnlockOk,
    payment_status: status.payment_status,
    generated_at_utc: new Date().toISOString(),
    reproduce: "npm run smoke:logos-inquiry-payapp-http:live",
    note: "Does not open payapp.kr redirect — feedback simulated locally",
  };

  mkdirSync(path.dirname(OUT), { recursive: true });
  writeFileSync(OUT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(
    JSON.stringify({
      ok: report.ok,
      out: OUT,
      prod_keys_in_use: report.prod_keys_in_use,
      pro_unlock: proUnlockOk,
    }),
  );
  if (!report.ok) process.exit(1);
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: String(err) }));
  process.exit(1);
});
