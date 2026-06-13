#!/usr/bin/env node
/**
 * Smoke: POST /api/leads/compression-pilot-audit and assert webhook delivery when env is set.
 * Loads projects/no1kmedi/.env.local then workspace .env (same order as other no1kmedi scripts).
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const no1kmediRoot = path.resolve(scriptDir, "..");
const workspaceRoot = path.resolve(scriptDir, "../../..");

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!m) continue;
    const key = m[1];
    if (process.env[key] !== undefined) continue;
    process.env[key] = m[2].trim().replace(/^["']|["']$/g, "");
  }
}

loadEnvFile(path.join(no1kmediRoot, ".env.local"));
loadEnvFile(path.join(workspaceRoot, ".env"));

const base = (process.env.NO1KMEDI_BASE_URL || "http://127.0.0.1:3010").replace(/\/$/, "");
const requireDeliver = process.argv.includes("--require-deliver");
const turnstileConfigured = Boolean(
  (process.env.NEXT_PUBLIC_TURNSTILE_SITEKEY || "").trim() &&
    (process.env.TURNSTILE_SECRET_KEY || "").trim(),
);
const turnstileSkipVerify = process.env.KM_TURNSTILE_SKIP_VERIFY === "1";

if (turnstileConfigured && !turnstileSkipVerify) {
  console.error(
    "[smoke-compression-pilot-audit-webhook] Turnstile keys set but KM_TURNSTILE_SKIP_VERIFY!=1 — add dev-only bypass to .env.local or omit turnstile keys for smoke",
  );
  process.exit(1);
}

const payload = {
  company_legal_name: "Webhook Smoke Co",
  country: "대한민국",
  company_stage: "pre_seed_startup",
  contact_name: "Ops Smoke",
  contact_email: "ops-smoke@example.com",
  contact_role: "Engineering",
  primary_domain: "customer_support",
  llm_provider: "openai",
  monthly_token_volume: "lt_10m",
  use_case_summary: "Webhook smoke test payload for compression pilot audit apply route.",
  masked_jsonl_readiness: "need_help",
  estimated_sample_rows: "20_50",
  pii_scrub_ack: true,
  nda_ack: true,
  not_sla_ack: true,
  no_guarantee_ack: true,
};

const res = await fetch(`${base}/api/leads/compression-pilot-audit`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});

const json = await res.json();
if (!res.ok || !json.success) {
  console.error("[smoke-compression-pilot-audit-webhook] failed", res.status, json);
  process.exit(1);
}

const wh = json.webhook || {};
console.log(
  `[smoke-compression-pilot-audit-webhook] ok application_id=${json.application_id} enabled=${wh.enabled} delivered=${wh.delivered} target=${wh.target || "n/a"}`,
);

if (requireDeliver && wh.enabled && !wh.delivered) {
  console.error("[smoke-compression-pilot-audit-webhook] webhook enabled but not delivered");
  process.exit(1);
}

if (requireDeliver && !wh.enabled) {
  console.error("[smoke-compression-pilot-audit-webhook] no webhook URL configured");
  process.exit(1);
}
