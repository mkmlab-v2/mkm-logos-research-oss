/**
 * Aggregate one-question funnel events from JSONL into summary_latest + summary_log.
 *
 * Usage:
 *   node scripts/aggregate-one-question-funnel.mjs
 *
 * Env:
 *   FUNNEL_EVENTS_JSONL_PATH (default reports/one_question_funnel_events.jsonl)
 *   FUNNEL_SUMMARY_OUT_PATH / FUNNEL_SUMMARY_JSON_PATH (default reports/one_question_funnel_summary_latest.json)
 *   FUNNEL_SUMMARY_LOG_PATH (default reports/one_question_funnel_summary_log.jsonl)
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function envPath(key, relDefault) {
  const v = String(process.env[key] || '').trim()
  return v ? path.resolve(v) : path.join(root, relDefault)
}

function readJsonl(filePath) {
  if (!fs.existsSync(filePath)) return []
  return fs
    .readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line)
      } catch {
        return null
      }
    })
    .filter(Boolean)
}

function n(v) {
  const x = Number(v)
  return Number.isFinite(x) ? x : 0
}

function pct(num, den) {
  if (!den || den <= 0) return 0
  return Number(((100 * num) / den).toFixed(2))
}

function isSyntheticRow(row) {
  const id = String(row?.requestId || '')
  return id.startsWith('seed_req_')
}

function main() {
  const inputPath = envPath('FUNNEL_EVENTS_JSONL_PATH', 'reports/one_question_funnel_events.jsonl')
  const outPath =
    String(process.env.FUNNEL_SUMMARY_OUT_PATH || process.env.FUNNEL_SUMMARY_JSON_PATH || '').trim()
      ? path.resolve(String(process.env.FUNNEL_SUMMARY_OUT_PATH || process.env.FUNNEL_SUMMARY_JSON_PATH))
      : path.join(root, 'reports/one_question_funnel_summary_latest.json')
  const logPath = envPath('FUNNEL_SUMMARY_LOG_PATH', 'reports/one_question_funnel_summary_log.jsonl')

  const rows = readJsonl(inputPath)
  let syntheticEventCount = 0
  for (const r of rows) {
    if (isSyntheticRow(r)) syntheticEventCount += 1
  }
  const totalEvents = rows.length
  const syntheticEventRatePct = pct(syntheticEventCount, totalEvents)

  let queryCount = 0
  let gateCount = 0
  let gatePassCount = 0
  let chargeCount = 0
  let chargeSuccessCount = 0
  let subscriptionViewCount = 0
  let purchaseAttemptCount = 0
  let purchaseSuccessCount = 0
  let errorCount = 0
  let evidenceOpenCount = 0
  let evidenceLinkClickCount = 0
  let additionalInputSubmitCount = 0
  let additionalInputQueryCount = 0
  let additionalInputGateCount = 0
  let additionalInputFollowupPassCount = 0
  let chargeAmountSum = 0

  for (const r of rows) {
    const ev = String(r.event || '')
    if (ev === 'one_question_query_received') {
      queryCount += 1
      if (String(r.label || '') === 'with_additional_input') additionalInputQueryCount += 1
    }
    if (ev === 'one_question_gate_decided') {
      gateCount += 1
      if (r.success === true) gatePassCount += 1
      if (String(r.label || '') === 'with_additional_input') {
        additionalInputGateCount += 1
        if (r.success === true) additionalInputFollowupPassCount += 1
      }
    }
    if (ev === 'one_question_charge_result') {
      chargeCount += 1
      if (r.success === true || r.charged === true) {
        chargeSuccessCount += 1
        chargeAmountSum += n(r.amountWon)
      }
    }
    if (ev === 'one_question_response_error') errorCount += 1
    if (ev === 'subscription_page_view') subscriptionViewCount += 1
    if (ev === 'subscription_purchase_result') {
      purchaseAttemptCount += 1
      if (r.success === true) purchaseSuccessCount += 1
    }
    if (ev === 'constitution_evidence_open') evidenceOpenCount += 1
    if (ev === 'constitution_evidence_link_click') evidenceLinkClickCount += 1
    if (ev === 'low_confidence_additional_input_submitted') additionalInputSubmitCount += 1
  }

  const gatePassRatePct = pct(gatePassCount, gateCount)
  const chargeSuccessRatePct = pct(chargeSuccessCount, chargeCount)
  const subscriptionPurchaseSuccessRatePct = pct(purchaseSuccessCount, purchaseAttemptCount)
  const queryToSubscriptionViewRatePct = pct(subscriptionViewCount, queryCount)
  const evidenceOpenRatePct = pct(evidenceOpenCount, queryCount)
  const evidenceLinkClickRatePct = pct(evidenceLinkClickCount, evidenceOpenCount)
  const additionalInputSubmitRatePct = pct(additionalInputSubmitCount, queryCount)
  const additionalInputFollowupGatePassRatePct = pct(additionalInputFollowupPassCount, additionalInputGateCount)
  const avgChargeAmountWon = chargeSuccessCount > 0 ? Number((chargeAmountSum / chargeSuccessCount).toFixed(2)) : 0

  const payload = {
    schema: 'one_question_funnel_summary_v1',
    generatedAt: new Date().toISOString(),
    inputPath,
    totalEvents,
    events: {
      queryCount,
      gateCount,
      chargeCount,
      subscriptionViewCount,
      purchaseAttemptCount,
      errorCount,
      evidenceOpenCount,
      evidenceLinkClickCount,
      additionalInputSubmitCount,
      additionalInputQueryCount,
      additionalInputGateCount,
      syntheticEventCount,
    },
    kpi: {
      gatePassRatePct,
      chargeSuccessRatePct,
      subscriptionPurchaseSuccessRatePct,
      queryToSubscriptionViewRatePct,
      evidenceOpenRatePct,
      evidenceLinkClickRatePct,
      additionalInputSubmitRatePct,
      additionalInputFollowupGatePassRatePct,
      syntheticEventRatePct,
      avgChargeAmountWon,
    },
    dataQuality: {
      syntheticEventCount,
      totalEvents,
      syntheticEventRatePct,
      syntheticLikely: syntheticEventRatePct > 5,
    },
  }

  fs.mkdirSync(path.dirname(outPath), { recursive: true })
  fs.writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  fs.mkdirSync(path.dirname(logPath), { recursive: true })
  fs.appendFileSync(logPath, `${JSON.stringify(payload)}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
}

main()
