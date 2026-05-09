#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");

const boardPath = path.join(projectRoot, "reports", "kpi", "five_axis_kpi_board_latest.json");

function fail(message) {
  console.error(`[check-5axis-kpi-board-schema] ${message}`);
  process.exit(1);
}

function isNonNegativeInt(v) {
  return Number.isInteger(v) && v >= 0;
}

function has(obj, key) {
  return obj != null && Object.prototype.hasOwnProperty.call(obj, key);
}

try {
  const raw = await readFile(boardPath, "utf8");
  const data = JSON.parse(raw);

  if (data.schema !== "five_axis_kpi_board_v1") fail("schema must be five_axis_kpi_board_v1");
  if (typeof data.generated_at_utc !== "string" || !data.generated_at_utc) fail("generated_at_utc missing");
  if (!Number.isInteger(data.window_days) || data.window_days <= 0) fail("window_days invalid");

  const kpis = data.kpis || {};
  const requiredKpiKeys = [
    "hub_ctr_proxy_clicks",
    "clinician_activation_proxy",
    "b2c_conversion_proxy_paid_orders",
    "b2b_inquiry_proxy",
    "showroom_to_hub_proxy",
  ];
  for (const key of requiredKpiKeys) {
    if (!has(kpis, key) || !isNonNegativeInt(kpis[key])) fail(`kpis.${key} invalid`);
  }
  const prevKpis = data.previous_kpis || {};
  for (const key of requiredKpiKeys) {
    if (!has(prevKpis, key) || !isNonNegativeInt(prevKpis[key])) fail(`previous_kpis.${key} invalid`);
  }
  const wow = data.wow_pct || {};
  for (const key of requiredKpiKeys) {
    if (!has(wow, key) || typeof wow[key] !== "number") fail(`wow_pct.${key} invalid`);
  }

  const detail = data.detail || {};
  const hub = detail.hub_clicks_by_target || {};
  const b2b = detail.b2b || {};
  const b2c = detail.b2c || {};
  const chatTiering = detail.chat_tiering || {};
  const premiumFunnel = detail.premium_payment_funnel || {};
  for (const key of ["showroom_jemaai", "premium_mkmlife", "b2b_acodeai"]) {
    if (!has(hub, key) || !isNonNegativeInt(hub[key])) fail(`detail.hub_clicks_by_target.${key} invalid`);
  }
  for (const key of ["submit_lead_events", "book_call_events"]) {
    if (!has(b2b, key) || !isNonNegativeInt(b2b[key])) fail(`detail.b2b.${key} invalid`);
  }
  if (!isNonNegativeInt(b2c.paid_orders)) fail("detail.b2c.paid_orders invalid");
  if (!isNonNegativeInt(b2c.requested_or_pending_or_paid)) fail("detail.b2c.requested_or_pending_or_paid invalid");
  if (typeof b2c.payment_success_rate_pct !== "number" || b2c.payment_success_rate_pct < 0) {
    fail("detail.b2c.payment_success_rate_pct invalid");
  }
  for (const key of ["total_rows", "premium_requested", "premium_served", "downgraded_count"]) {
    if (!has(chatTiering, key) || !isNonNegativeInt(chatTiering[key])) fail(`detail.chat_tiering.${key} invalid`);
  }
  for (const key of ["premium_service_rate_pct", "downgrade_rate_pct", "avg_response_len_chars"]) {
    if (!has(chatTiering, key) || typeof chatTiering[key] !== "number" || chatTiering[key] < 0) {
      fail(`detail.chat_tiering.${key} invalid`);
    }
  }
  for (const key of ["payment_start_count", "payment_redirect_count", "verified_total", "verified_ok_count", "verified_pending_count", "verified_error_count"]) {
    if (!has(premiumFunnel, key) || !isNonNegativeInt(premiumFunnel[key])) {
      fail(`detail.premium_payment_funnel.${key} invalid`);
    }
  }
  for (const key of ["redirect_rate_pct", "verified_ok_rate_pct", "verified_pending_rate_pct"]) {
    if (!has(premiumFunnel, key) || typeof premiumFunnel[key] !== "number" || premiumFunnel[key] < 0) {
      fail(`detail.premium_payment_funnel.${key} invalid`);
    }
  }

  if (!Array.isArray(data.notes)) fail("notes must be array");

  console.log("[check-5axis-kpi-board-schema] passed.");
} catch (error) {
  const msg = error instanceof Error ? error.message : String(error);
  fail(`failed: ${msg}`);
}
