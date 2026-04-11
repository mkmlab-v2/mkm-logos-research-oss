/**
 * Derive KPI threshold presets (conservative / balanced / aggressive) from latest summary.
 *
 * Usage:
 *   node scripts/derive-one-question-threshold-presets.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function readJson(p) {
  if (!fs.existsSync(p)) return null
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'))
  } catch {
    return null
  }
}

function n(v) {
  const x = Number(v)
  return Number.isFinite(x) ? x : 0
}

function clamp(x, lo, hi) {
  return Math.min(hi, Math.max(lo, x))
}

function floorPct(observed, mult, floor, cap) {
  const raw = n(observed) * mult
  return clamp(Number(raw.toFixed(2)), floor, cap)
}

function main() {
  const summaryPath = path.join(root, 'reports/one_question_funnel_summary_latest.json')
  const outPath = path.join(root, 'reports/one_question_funnel_threshold_presets_latest.json')
  const summary = readJson(summaryPath)
  const kpi = summary?.kpi || {}
  const ev = summary?.events || {}

  const base = {
    MIN_QUERY_COUNT: 40,
    MIN_GATE_PASS_RATE_PCT: floorPct(kpi.gatePassRatePct, 0.9, 50, 95),
    MIN_CHARGE_SUCCESS_RATE_PCT: floorPct(kpi.chargeSuccessRatePct, 0.9, 40, 95),
    MIN_SUBSCRIPTION_PURCHASE_SUCCESS_RATE_PCT: floorPct(
      kpi.subscriptionPurchaseSuccessRatePct,
      0.85,
      15,
      90
    ),
    MIN_QUERY_TO_SUBSCRIPTION_VIEW_RATE_PCT: floorPct(kpi.queryToSubscriptionViewRatePct, 0.85, 10, 80),
    MIN_EVIDENCE_OPEN_RATE_PCT: floorPct(kpi.evidenceOpenRatePct, 0.85, 10, 80),
    MIN_EVIDENCE_LINK_CLICK_RATE_PCT: floorPct(kpi.evidenceLinkClickRatePct, 0.85, 10, 90),
    MIN_ADDITIONAL_INPUT_SUBMIT_RATE_PCT: floorPct(kpi.additionalInputSubmitRatePct, 0.85, 5, 80),
    MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT: floorPct(
      kpi.additionalInputFollowupGatePassRatePct,
      0.9,
      50,
      98
    ),
    MAX_SYNTHETIC_EVENT_RATE_PCT: 5,
  }

  const scale = (m) => ({
    MIN_QUERY_COUNT: Math.max(20, Math.round(base.MIN_QUERY_COUNT * m)),
    MIN_GATE_PASS_RATE_PCT: clamp(base.MIN_GATE_PASS_RATE_PCT * (m > 1 ? 0.95 : 1.05 * m), 45, 98),
    MIN_CHARGE_SUCCESS_RATE_PCT: clamp(base.MIN_CHARGE_SUCCESS_RATE_PCT * (m > 1 ? 0.97 : 1.03 * m), 35, 98),
    MIN_SUBSCRIPTION_PURCHASE_SUCCESS_RATE_PCT: clamp(
      base.MIN_SUBSCRIPTION_PURCHASE_SUCCESS_RATE_PCT * (m > 1 ? 0.95 : 1.05 * m),
      10,
      95
    ),
    MIN_QUERY_TO_SUBSCRIPTION_VIEW_RATE_PCT: clamp(
      base.MIN_QUERY_TO_SUBSCRIPTION_VIEW_RATE_PCT * (m > 1 ? 0.95 : 1.05 * m),
      8,
      85
    ),
    MIN_EVIDENCE_OPEN_RATE_PCT: clamp(base.MIN_EVIDENCE_OPEN_RATE_PCT * (m > 1 ? 0.95 : 1.05 * m), 8, 85),
    MIN_EVIDENCE_LINK_CLICK_RATE_PCT: clamp(
      base.MIN_EVIDENCE_LINK_CLICK_RATE_PCT * (m > 1 ? 0.95 : 1.05 * m),
      8,
      92
    ),
    MIN_ADDITIONAL_INPUT_SUBMIT_RATE_PCT: clamp(
      base.MIN_ADDITIONAL_INPUT_SUBMIT_RATE_PCT * (m > 1 ? 0.95 : 1.05 * m),
      5,
      85
    ),
    MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT: clamp(
      base.MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT * (m > 1 ? 0.97 : 1.02 * m),
      45,
      99
    ),
    MAX_SYNTHETIC_EVENT_RATE_PCT: base.MAX_SYNTHETIC_EVENT_RATE_PCT,
  })

  const payload = {
    schema: 'one_question_funnel_threshold_presets_v1',
    generatedAt: new Date().toISOString(),
    summaryPath,
    observedQueryCount: n(ev.queryCount),
    profiles: {
      conservative: scale(1.12),
      balanced: scale(1),
      aggressive: scale(0.88),
    },
  }

  fs.mkdirSync(path.dirname(outPath), { recursive: true })
  fs.writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
}

main()
