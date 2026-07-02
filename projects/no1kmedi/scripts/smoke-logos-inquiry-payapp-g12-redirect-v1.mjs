/**
 * G12 staging: validate PayApp redirect URL with real mul_no (keys from env only).
 * Does NOT open payapp.kr — no live charge.
 * Skips exit 0 when PAYAPP_KEY/PAYAPP_VALUE absent.
 */
import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../../..");
const OUT = path.join(ROOT, "reports/logos_inquiry_payapp_g12_redirect_smoke_v1_latest.json");

const base = (
  process.argv.find((a) => a.startsWith("--base="))?.slice(7) ||
  process.argv[process.argv.indexOf("--base") + 1] ||
  "http://localhost:3010"
).replace(/\/$/, "");

function fingerprint(value) {
  if (!value) return "";
  return `sha256:${createHash("sha256").update(value).digest("hex").slice(0, 12)}`;
}

function validateRedirect(url, orderId, amount) {
  const u = new URL(url);
  const checks = {
    host_ok: u.protocol === "https:" && u.hostname === "api.payapp.kr",
    path_ok: u.pathname.startsWith("/oapi/pay"),
    mul_no_present: Boolean(u.searchParams.get("mul_no")),
    ordr_idxx_matches: u.searchParams.get("ordr_idxx") === orderId,
    good_mny_present: Boolean(u.searchParams.get("good_mny")),
    good_mny_matches: u.searchParams.get("good_mny") === String(amount),
    feedbackurl_present: Boolean(u.searchParams.get("feedbackurl")),
    return_url_present: Boolean(u.searchParams.get("return_url")),
    not_dry_run_mul_no: u.searchParams.get("mul_no") !== "dry_run_key",
  };
  return { ok: Object.values(checks).every(Boolean), checks };
}

async function main() {
  const payappKey = (process.env.PAYAPP_KEY || "").trim();
  const payappValue = (process.env.PAYAPP_VALUE || "").trim();
  const testEmail = `logos-g12-redirect-${Date.now()}@example.com`;
  const amount = 39000;

  if (!payappKey || !payappValue) {
    const skipped = {
      schema: "logos_inquiry_payapp_g12_redirect_smoke_v1",
      ok: true,
      skipped: true,
      reason: "g12_not_injected",
      mode: "staging_redirect_probe",
      send_gate: "HOLD",
      g12_ready: false,
      generated_at_utc: new Date().toISOString(),
      reproduce: "PAYAPP_KEY=... PAYAPP_VALUE=... npm run smoke:logos-inquiry-payapp-g12-redirect",
      inject_hint: "G12: set keys in workspace .env then re-run",
    };
    mkdirSync(path.dirname(OUT), { recursive: true });
    writeFileSync(OUT, `${JSON.stringify(skipped, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({ ok: true, skipped: true, out: OUT }));
    return;
  }

  const intentRes = await fetch(`${base}/api/logos-research/billing/intent?sku=pro`);
  const intent = await intentRes.json();
  if (!intentRes.ok) throw new Error(`intent_failed status=${intentRes.status}`);

  const createRes = await fetch(`${base}/api/payment/payapp/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      payapp_key: payappKey,
      payapp_value: payappValue,
      email: testEmail,
      plan_code: intent.plan_code || "logos_inquiry_pro_v1",
      product_name: intent.product_name_ko || "Logos Inquiry Pro",
      amount: intent.amount_krw || amount,
      return_url: intent.return_url,
    }),
  });
  const created = await createRes.json();
  if (!createRes.ok || !created.success || !created.redirect_url) {
    throw new Error(`create_failed status=${createRes.status}`);
  }

  const redirectCheck = validateRedirect(
    created.redirect_url,
    created.order_id,
    intent.amount_krw || amount,
  );
  if (!redirectCheck.ok) {
    throw new Error(`redirect_invalid ${JSON.stringify(redirectCheck.checks)}`);
  }

  const checkoutRes = await fetch(`${base}/api/logos-research/billing/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: testEmail }),
  });
  const checkout = await checkoutRes.json();
  const serverG12 = checkout.prod_keys_in_use === true;

  const report = {
    schema: "logos_inquiry_payapp_g12_redirect_smoke_v1",
    ok: true,
    skipped: false,
    mode: "staging_redirect_only",
    send_gate: intent.send_gate || "HOLD",
    base,
    g12_ready: true,
    payapp_key_fingerprint: fingerprint(payappKey),
    order_id: created.order_id,
    redirect_validated: true,
    redirect_checks: redirectCheck.checks,
    server_checkout_prod_keys: serverG12,
    server_g12_pending: !serverG12,
    server_g12_hint: serverG12
      ? null
      : "Restart dev with PAYAPP_KEY in process env (Import-WorkspaceDotEnv) for checkout server path",
    generated_at_utc: new Date().toISOString(),
    reproduce: "npm run smoke:logos-inquiry-payapp-g12-redirect",
    note: "Redirect URL validated only — payapp.kr not opened",
  };

  mkdirSync(path.dirname(OUT), { recursive: true });
  writeFileSync(OUT, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(
    JSON.stringify({
      ok: true,
      out: OUT,
      redirect_validated: true,
      server_g12_pending: !serverG12,
    }),
  );
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: String(err) }));
  process.exit(1);
});
