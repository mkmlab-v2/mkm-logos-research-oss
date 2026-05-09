#!/usr/bin/env node

import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const memoryDir = path.join(projectRoot, "memory", "commercialization");
const outDir = path.join(projectRoot, "reports", "kpi");

const eventsPath = path.join(memoryDir, "hub_events.jsonl");
const paymentsPath = path.join(memoryDir, "payapp_payments.json");
const jsonOut = path.join(outDir, "five_axis_kpi_board_latest.json");
const mdOut = path.join(outDir, "five_axis_kpi_board_latest.md");

function safeDate(value) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function isWithinDays(iso, days) {
  const d = safeDate(iso);
  if (!d) return false;
  const cut = Date.now() - days * 24 * 60 * 60 * 1000;
  return d.getTime() >= cut;
}

function isBetweenDays(iso, fromDaysAgo, toDaysAgo) {
  const d = safeDate(iso);
  if (!d) return false;
  const now = Date.now();
  const from = now - fromDaysAgo * 24 * 60 * 60 * 1000;
  const to = now - toDaysAgo * 24 * 60 * 60 * 1000;
  return d.getTime() >= from && d.getTime() < to;
}

async function readJsonFile(filePath, fallback) {
  try {
    const raw = await readFile(filePath, "utf8");
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

async function readJsonl(filePath) {
  try {
    const raw = await readFile(filePath, "utf8");
    return raw
      .split(/\r?\n/)
      .filter((line) => line.trim().length > 0)
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return null;
        }
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

function pct(numerator, denominator) {
  if (!denominator) return 0;
  return Number(((numerator / denominator) * 100).toFixed(2));
}

const [events, payments] = await Promise.all([readJsonl(eventsPath), readJsonFile(paymentsPath, [])]);

const last7Events = events.filter((e) => isWithinDays(e.ts_utc, 7));
const last7Payments = payments.filter((p) => isWithinDays(p.updated_at || p.created_at, 7));
const prev7Events = events.filter((e) => isBetweenDays(e.ts_utc, 14, 7));
const prev7Payments = payments.filter((p) => isBetweenDays(p.updated_at || p.created_at, 14, 7));

const hubClicks = last7Events.filter((e) => e.event === "click_hub_cross_cta");
const hubClicksByTarget = {
  showroom_jemaai: hubClicks.filter((e) => e.target_surface === "showroom_jemaai").length,
  premium_mkmlife: hubClicks.filter((e) => e.target_surface === "premium_mkmlife").length,
  b2b_acodeai: hubClicks.filter((e) => e.target_surface === "b2b_acodeai").length,
};

const clinicianStarts = new Set(
  last7Events
    .filter((e) => e.event === "view_clinician_workspace")
    .map((e) => String(e.session_id || "").trim())
    .filter((id) => id.length > 0)
).size;

const b2bLeads = last7Events.filter((e) => e.event === "submit_lead").length;
const b2bCallClicks = last7Events.filter((e) => e.event === "book_call").length;
const tierRows = last7Events.filter((e) => e.event === "chat_answer_tier_result");
const premiumRequested = tierRows.filter((e) => e.requested_level === "premium").length;
const premiumServed = tierRows.filter((e) => e.effective_level === "premium").length;
const downgradedCount = tierRows.filter((e) => String(e.access_gate || "ok") !== "ok").length;
const tierAvgResponseLen = tierRows.length
  ? Number((tierRows.reduce((acc, row) => acc + Number(row.response_len || 0), 0) / tierRows.length).toFixed(2))
  : 0;
const premiumPaymentStart = last7Events.filter((e) => e.event === "premium_payment_start").length;
const premiumPaymentRedirect = last7Events.filter((e) => e.event === "premium_payment_redirect").length;
const premiumAccessVerifiedRows = last7Events.filter((e) => e.event === "premium_access_verified");
const premiumAccessVerifiedOk = premiumAccessVerifiedRows.filter((e) => e.result === "ok").length;
const premiumAccessVerifiedPending = premiumAccessVerifiedRows.filter((e) => e.result === "pending").length;
const premiumAccessVerifiedError = premiumAccessVerifiedRows.filter((e) => e.result === "error").length;

const paidCount = last7Payments.filter((p) => p.state === "paid").length;
const requestedCount = last7Payments.filter((p) => ["requested", "pending", "paid"].includes(p.state)).length;

const prevHubClicks = prev7Events.filter((e) => e.event === "click_hub_cross_cta").length;
const prevClinicianStarts = new Set(
  prev7Events
    .filter((e) => e.event === "view_clinician_workspace")
    .map((e) => String(e.session_id || "").trim())
    .filter((id) => id.length > 0)
).size;
const prevB2bLeads = prev7Events.filter((e) => e.event === "submit_lead").length;
const prevB2bCallClicks = prev7Events.filter((e) => e.event === "book_call").length;
const prevPaidCount = prev7Payments.filter((p) => p.state === "paid").length;
const prevShowroomToHub = prev7Events.filter(
  (e) => e.event === "click_hub_cross_cta" && e.target_surface === "showroom_jemaai"
).length;
const prevTierRows = prev7Events.filter((e) => e.event === "chat_answer_tier_result");
const prevPremiumRequested = prevTierRows.filter((e) => e.requested_level === "premium").length;
const prevPremiumServed = prevTierRows.filter((e) => e.effective_level === "premium").length;
const prevDowngradedCount = prevTierRows.filter((e) => String(e.access_gate || "ok") !== "ok").length;
const prevPremiumPaymentStart = prev7Events.filter((e) => e.event === "premium_payment_start").length;
const prevPremiumPaymentRedirect = prev7Events.filter((e) => e.event === "premium_payment_redirect").length;
const prevPremiumAccessVerifiedRows = prev7Events.filter((e) => e.event === "premium_access_verified");
const prevPremiumAccessVerifiedOk = prevPremiumAccessVerifiedRows.filter((e) => e.result === "ok").length;
const prevPremiumAccessVerifiedPending = prevPremiumAccessVerifiedRows.filter((e) => e.result === "pending").length;

function wow(current, previous) {
  if (!previous) return 0;
  return Number((((current - previous) / previous) * 100).toFixed(2));
}

const board = {
  schema: "five_axis_kpi_board_v1",
  generated_at_utc: new Date().toISOString(),
  window_days: 7,
  sources: {
    events_jsonl: path.relative(projectRoot, eventsPath).replace(/\\/g, "/"),
    payments_json: path.relative(projectRoot, paymentsPath).replace(/\\/g, "/"),
  },
  kpis: {
    hub_ctr_proxy_clicks: hubClicks.length,
    clinician_activation_proxy: clinicianStarts,
    b2c_conversion_proxy_paid_orders: paidCount,
    b2b_inquiry_proxy: b2bLeads + b2bCallClicks,
    showroom_to_hub_proxy: hubClicksByTarget.showroom_jemaai,
  },
  previous_kpis: {
    hub_ctr_proxy_clicks: prevHubClicks,
    clinician_activation_proxy: prevClinicianStarts,
    b2c_conversion_proxy_paid_orders: prevPaidCount,
    b2b_inquiry_proxy: prevB2bLeads + prevB2bCallClicks,
    showroom_to_hub_proxy: prevShowroomToHub,
  },
  wow_pct: {
    hub_ctr_proxy_clicks: wow(hubClicks.length, prevHubClicks),
    clinician_activation_proxy: wow(clinicianStarts, prevClinicianStarts),
    b2c_conversion_proxy_paid_orders: wow(paidCount, prevPaidCount),
    b2b_inquiry_proxy: wow(b2bLeads + b2bCallClicks, prevB2bLeads + prevB2bCallClicks),
    showroom_to_hub_proxy: wow(hubClicksByTarget.showroom_jemaai, prevShowroomToHub),
  },
  detail: {
    hub_clicks_by_target: hubClicksByTarget,
    b2b: {
      submit_lead_events: b2bLeads,
      book_call_events: b2bCallClicks,
    },
    b2c: {
      paid_orders: paidCount,
      requested_or_pending_or_paid: requestedCount,
      payment_success_rate_pct: pct(paidCount, requestedCount),
    },
    chat_tiering: {
      total_rows: tierRows.length,
      premium_requested: premiumRequested,
      premium_served: premiumServed,
      premium_service_rate_pct: pct(premiumServed, premiumRequested),
      downgraded_count: downgradedCount,
      downgrade_rate_pct: pct(downgradedCount, tierRows.length),
      avg_response_len_chars: tierAvgResponseLen,
      wow_premium_served_pct: wow(premiumServed, prevPremiumServed),
      wow_downgraded_pct: wow(downgradedCount, prevDowngradedCount),
      wow_premium_requested_pct: wow(premiumRequested, prevPremiumRequested),
    },
    premium_payment_funnel: {
      payment_start_count: premiumPaymentStart,
      payment_redirect_count: premiumPaymentRedirect,
      redirect_rate_pct: pct(premiumPaymentRedirect, premiumPaymentStart),
      verified_total: premiumAccessVerifiedRows.length,
      verified_ok_count: premiumAccessVerifiedOk,
      verified_pending_count: premiumAccessVerifiedPending,
      verified_error_count: premiumAccessVerifiedError,
      verified_ok_rate_pct: pct(premiumAccessVerifiedOk, premiumAccessVerifiedRows.length),
      verified_pending_rate_pct: pct(premiumAccessVerifiedPending, premiumAccessVerifiedRows.length),
      wow_payment_start_pct: wow(premiumPaymentStart, prevPremiumPaymentStart),
      wow_payment_redirect_pct: wow(premiumPaymentRedirect, prevPremiumPaymentRedirect),
      wow_verified_ok_pct: wow(premiumAccessVerifiedOk, prevPremiumAccessVerifiedOk),
      wow_verified_pending_pct: wow(premiumAccessVerifiedPending, prevPremiumAccessVerifiedPending),
    },
  },
  notes: [
    "Proxy metrics are event-based until GA/GTM and full funnel stitching is enabled.",
    "Clinician activation now uses workspace view events and should be upgraded to authenticated session KPI later.",
  ],
};

const md = [
  "# 5-Axis KPI Board (Latest)",
  "",
  `- Generated (UTC): ${board.generated_at_utc}`,
  `- Window: last ${board.window_days} days`,
  "",
  "## KPI Snapshot",
  `- Hub CTR proxy clicks: ${board.kpis.hub_ctr_proxy_clicks}`,
  `- Clinician activation proxy: ${board.kpis.clinician_activation_proxy}`,
  `- B2C conversion proxy (paid orders): ${board.kpis.b2c_conversion_proxy_paid_orders}`,
  `- B2B inquiry proxy: ${board.kpis.b2b_inquiry_proxy}`,
  `- Showroom-to-hub proxy clicks: ${board.kpis.showroom_to_hub_proxy}`,
  "",
  "## WoW (%)",
  `- Hub CTR proxy: ${board.wow_pct.hub_ctr_proxy_clicks}%`,
  `- Clinician activation proxy: ${board.wow_pct.clinician_activation_proxy}%`,
  `- B2C conversion proxy (paid orders): ${board.wow_pct.b2c_conversion_proxy_paid_orders}%`,
  `- B2B inquiry proxy: ${board.wow_pct.b2b_inquiry_proxy}%`,
  `- Showroom-to-hub proxy: ${board.wow_pct.showroom_to_hub_proxy}%`,
  "",
  "## Detail",
  `- Hub target clicks: ${JSON.stringify(board.detail.hub_clicks_by_target)}`,
  `- B2B events: ${JSON.stringify(board.detail.b2b)}`,
  `- B2C payment detail: ${JSON.stringify(board.detail.b2c)}`,
  `- Chat tiering detail: ${JSON.stringify(board.detail.chat_tiering)}`,
  `- Premium payment funnel detail: ${JSON.stringify(board.detail.premium_payment_funnel)}`,
  "",
  "## Notes",
  ...board.notes.map((n) => `- ${n}`),
  "",
].join("\n");

await mkdir(outDir, { recursive: true });
await writeFile(jsonOut, JSON.stringify(board, null, 2) + "\n", "utf8");
await writeFile(mdOut, md, "utf8");

console.log(`[build-5axis-kpi-board] wrote ${path.relative(projectRoot, jsonOut)}`);
console.log(`[build-5axis-kpi-board] wrote ${path.relative(projectRoot, mdOut)}`);
