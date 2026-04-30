#!/usr/bin/env node
const BASE_URL = process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010";
const ADMIN_TOKEN = process.env.NO1KMEDI_ADMIN_TOKEN || "dev-admin-token";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function request(path, init) {
  const res = await fetch(`${BASE_URL}${path}`, init);
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = { raw: text };
  }
  return { res, json };
}

async function main() {
  const email = `smoke-flow+${Date.now()}@jema-ai.com`;
  const emailQuery = encodeURIComponent(email);

  const initial = await request(`/api/member/access-status?email=${emailQuery}`, { method: "GET" });
  assert(initial.res.status === 200, `initial access-status expected 200, got ${initial.res.status}`);
  assert(initial.json?.can_use_pro_clinical_assist === false, "initial user should be locked");

  const create = await request("/api/payment/payapp/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      payapp_key: "test-key",
      payapp_value: "test-value",
      email,
      plan_code: "clinical-assist-pro",
      product_name: "MKM Hanui Clinical Assistant",
      amount: 39000,
    }),
  });
  assert(create.res.status === 200, `payapp create expected 200, got ${create.res.status}`);
  const orderId = create.json?.order_id;
  assert(typeof orderId === "string" && orderId.length > 0, "order_id missing");

  const feedback = await request("/api/payment/payapp/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_id: orderId, status: "paid", email, plan_code: "clinical-assist-pro" }),
  });
  assert(feedback.res.status === 200, `payapp feedback expected 200, got ${feedback.res.status}`);

  const submit = await request("/api/member/verification/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      clinic_name: "스모크한의원",
      biz_number: "123-45-67890",
      license_number: "MDK-TEST-0001",
    }),
  });
  assert(submit.res.status === 200, `verification submit expected 200, got ${submit.res.status}`);
  const verificationId = submit.json?.verification_id;
  assert(typeof verificationId === "string" && verificationId.length > 0, "verification_id missing");

  const review = await request("/api/member/verification/review", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-no1kmedi-admin-token": ADMIN_TOKEN,
    },
    body: JSON.stringify({ verification_id: verificationId, decision: "approved", admin_token: ADMIN_TOKEN }),
  });
  assert(review.res.status === 200, `verification review expected 200, got ${review.res.status}`);

  const finalStatus = await request(`/api/member/access-status?email=${emailQuery}`, { method: "GET" });
  assert(finalStatus.res.status === 200, `final access-status expected 200, got ${finalStatus.res.status}`);
  assert(finalStatus.json?.can_use_pro_clinical_assist === true, "final user should be unlocked");

  console.log("smoke-member-access-flow passed");
}

main().catch((error) => {
  console.error("smoke-member-access-flow failed:", error.message);
  process.exit(1);
});
