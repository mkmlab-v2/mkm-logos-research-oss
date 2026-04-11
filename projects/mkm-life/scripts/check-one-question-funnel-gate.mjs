/**
 * Evaluate funnel KPIs against threshold preset profile. Writes gate_latest + gate_log.
 *
 * Usage:
 *   node scripts/check-one-question-funnel-gate.mjs
 *
 * Env: THRESHOLD_PROFILE, FUNNEL_SUMMARY_JSON_PATH, FUNNEL_GATE_OUT_PATH, FUNNEL_GATE_LOG_PATH,
 *      REQUIRE_REAL_DATA_GATE, MAX_SYNTHETIC_EVENT_RATE_PCT (override preset max),
 *      MIN_EVIDENCE_OPEN_SAMPLES_FOR_LINK_CHECK (default 10),
 *      MIN_ADDITIONAL_INPUT_GATE_SAMPLE_COUNT (default 5)
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

function envNum(key, def) {
  const v = String(process.env[key] || '').trim()
  if (!v) return def
  const x = Number(v)
  return Number.isFinite(x) ? x : def
}

function main() {
  const profile = String(process.env.THRESHOLD_PROFILE || 'balanced').trim() || 'balanced'
  const summaryPath = String(process.env.FUNNEL_SUMMARY_JSON_PATH || '').trim()
    ? path.resolve(process.env.FUNNEL_SUMMARY_JSON_PATH)
    : path.join(root, 'reports/one_question_funnel_summary_latest.json')
  const presetPath = path.join(root, 'reports/one_question_funnel_threshold_presets_latest.json')
  const gateOut = String(process.env.FUNNEL_GATE_OUT_PATH || '').trim()
    ? path.resolve(process.env.FUNNEL_GATE_OUT_PATH)
    : path.join(root, 'reports/one_question_funnel_gate_latest.json')
  const gateLog = String(process.env.FUNNEL_GATE_LOG_PATH || '').trim()
    ? path.resolve(process.env.FUNNEL_GATE_LOG_PATH)
    : path.join(root, 'reports/one_question_funnel_gate_log.jsonl')

  const summary = readJson(summaryPath)
  const presets = readJson(presetPath)
  const thr = presets?.profiles?.[profile] || presets?.profiles?.balanced || null

  const defaults = {
    MIN_QUERY_COUNT: 40,
    MIN_GATE_PASS_RATE_PCT: 64,
    MIN_CHARGE_SUCCESS_RATE_PCT: 60,
    MIN_SUBSCRIPTION_PURCHASE_SUCCESS_RATE_PCT: 20,
    MIN_QUERY_TO_SUBSCRIPTION_VIEW_RATE_PCT: 15,
    MIN_EVIDENCE_OPEN_RATE_PCT: 15,
    MIN_EVIDENCE_LINK_CLICK_RATE_PCT: 20,
    MIN_ADDITIONAL_INPUT_SUBMIT_RATE_PCT: 15,
    MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT: 90,
    MAX_SYNTHETIC_EVENT_RATE_PCT: envNum('MAX_SYNTHETIC_EVENT_RATE_PCT', 5),
  }

  const T = thr
    ? {
        MIN_QUERY_COUNT: n(thr.MIN_QUERY_COUNT),
        MIN_GATE_PASS_RATE_PCT: n(thr.MIN_GATE_PASS_RATE_PCT),
        MIN_CHARGE_SUCCESS_RATE_PCT: n(thr.MIN_CHARGE_SUCCESS_RATE_PCT),
        MIN_SUBSCRIPTION_PURCHASE_SUCCESS_RATE_PCT: n(thr.MIN_SUBSCRIPTION_PURCHASE_SUCCESS_RATE_PCT),
        MIN_QUERY_TO_SUBSCRIPTION_VIEW_RATE_PCT: n(thr.MIN_QUERY_TO_SUBSCRIPTION_VIEW_RATE_PCT),
        MIN_EVIDENCE_OPEN_RATE_PCT: n(thr.MIN_EVIDENCE_OPEN_RATE_PCT),
        MIN_EVIDENCE_LINK_CLICK_RATE_PCT: n(thr.MIN_EVIDENCE_LINK_CLICK_RATE_PCT),
        MIN_ADDITIONAL_INPUT_SUBMIT_RATE_PCT: n(thr.MIN_ADDITIONAL_INPUT_SUBMIT_RATE_PCT),
        MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT: n(thr.MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT),
        MAX_SYNTHETIC_EVENT_RATE_PCT: n(thr.MAX_SYNTHETIC_EVENT_RATE_PCT),
      }
    : defaults

  if (String(process.env.MAX_SYNTHETIC_EVENT_RATE_PCT || '').trim()) {
    T.MAX_SYNTHETIC_EVENT_RATE_PCT = envNum('MAX_SYNTHETIC_EVENT_RATE_PCT', T.MAX_SYNTHETIC_EVENT_RATE_PCT)
  }

  const ev = summary?.events || {}
  const kpi = summary?.kpi || {}
  const queryCount = n(ev.queryCount)
  const evidenceOpens = n(ev.evidenceOpenCount)
  const addInputGates = n(ev.additionalInputGateCount)
  const minEvidenceSamples = envNum('MIN_EVIDENCE_OPEN_SAMPLES_FOR_LINK_CHECK', 10)
  const minAddGateSamples = envNum('MIN_ADDITIONAL_INPUT_GATE_SAMPLE_COUNT', 5)
  const requireReal = String(process.env.REQUIRE_REAL_DATA_GATE || '').trim() === '1'

  const checks = []

  const add = (name, actual, minimum, extra = {}) => {
    const pass = extra.skipped === true ? true : n(actual) >= n(minimum)
    checks.push({
      name,
      actual: n(actual),
      minimum: n(minimum),
      pass,
      ...extra,
    })
  }

  const skipNoQueries = (name, actual, minimum) => {
    checks.push({
      name,
      actual: n(actual),
      minimum: n(minimum),
      pass: true,
      skipped: true,
      skipReason: 'no_queries_yet',
    })
  }

  const noQueries = queryCount === 0

  add('query_count', queryCount, T.MIN_QUERY_COUNT)

  if (noQueries) {
    skipNoQueries('gate_pass_rate_pct', kpi.gatePassRatePct, T.MIN_GATE_PASS_RATE_PCT)
    skipNoQueries('charge_success_rate_pct', kpi.chargeSuccessRatePct, T.MIN_CHARGE_SUCCESS_RATE_PCT)
    skipNoQueries(
      'subscription_purchase_success_rate_pct',
      kpi.subscriptionPurchaseSuccessRatePct,
      T.MIN_SUBSCRIPTION_PURCHASE_SUCCESS_RATE_PCT
    )
    skipNoQueries(
      'query_to_subscription_view_rate_pct',
      kpi.queryToSubscriptionViewRatePct,
      T.MIN_QUERY_TO_SUBSCRIPTION_VIEW_RATE_PCT
    )
    skipNoQueries('evidence_open_rate_pct', kpi.evidenceOpenRatePct, T.MIN_EVIDENCE_OPEN_RATE_PCT)
    skipNoQueries('evidence_link_click_rate_pct', kpi.evidenceLinkClickRatePct, T.MIN_EVIDENCE_LINK_CLICK_RATE_PCT)
    skipNoQueries(
      'additional_input_submit_rate_pct',
      kpi.additionalInputSubmitRatePct,
      T.MIN_ADDITIONAL_INPUT_SUBMIT_RATE_PCT
    )
    skipNoQueries(
      'additional_input_followup_gate_pass_rate_pct',
      kpi.additionalInputFollowupGatePassRatePct,
      T.MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT
    )
  } else {
    add('gate_pass_rate_pct', kpi.gatePassRatePct, T.MIN_GATE_PASS_RATE_PCT)
    add('charge_success_rate_pct', kpi.chargeSuccessRatePct, T.MIN_CHARGE_SUCCESS_RATE_PCT)
    add(
      'subscription_purchase_success_rate_pct',
      kpi.subscriptionPurchaseSuccessRatePct,
      T.MIN_SUBSCRIPTION_PURCHASE_SUCCESS_RATE_PCT
    )
    add(
      'query_to_subscription_view_rate_pct',
      kpi.queryToSubscriptionViewRatePct,
      T.MIN_QUERY_TO_SUBSCRIPTION_VIEW_RATE_PCT
    )
    add('evidence_open_rate_pct', kpi.evidenceOpenRatePct, T.MIN_EVIDENCE_OPEN_RATE_PCT)

    if (evidenceOpens < minEvidenceSamples) {
      checks.push({
        name: 'evidence_link_click_rate_pct',
        actual: n(kpi.evidenceLinkClickRatePct),
        minimum: n(T.MIN_EVIDENCE_LINK_CLICK_RATE_PCT),
        pass: true,
        skipped: true,
        skipReason: `insufficient_evidence_open_samples(<${minEvidenceSamples})`,
      })
    } else {
      add('evidence_link_click_rate_pct', kpi.evidenceLinkClickRatePct, T.MIN_EVIDENCE_LINK_CLICK_RATE_PCT)
    }

    add(
      'additional_input_submit_rate_pct',
      kpi.additionalInputSubmitRatePct,
      T.MIN_ADDITIONAL_INPUT_SUBMIT_RATE_PCT
    )

    if (addInputGates < minAddGateSamples) {
      checks.push({
        name: 'additional_input_followup_gate_pass_rate_pct',
        actual: n(kpi.additionalInputFollowupGatePassRatePct),
        minimum: n(T.MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT),
        pass: true,
        skipped: true,
        skipReason: `insufficient_additional_input_gate_samples(<${minAddGateSamples})`,
      })
    } else {
      add(
        'additional_input_followup_gate_pass_rate_pct',
        kpi.additionalInputFollowupGatePassRatePct,
        T.MIN_ADDITIONAL_INPUT_FOLLOWUP_GATE_PASS_RATE_PCT
      )
    }
  }

  const synRate = n(kpi.syntheticEventRatePct)
  const synCheck = {
    name: 'synthetic_event_rate_pct',
    actual: synRate,
    minimum: 0,
    maximum: n(T.MAX_SYNTHETIC_EVENT_RATE_PCT),
    pass: synRate <= n(T.MAX_SYNTHETIC_EVENT_RATE_PCT),
    skipped: !requireReal,
    skipReason: !requireReal ? 'REQUIRE_REAL_DATA_GATE not set' : undefined,
  }
  if (!requireReal) synCheck.pass = true
  checks.push(synCheck)

  const ok = checks.every((c) => c.pass === true)

  const payload = {
    schema: 'one_question_funnel_gate_v1',
    generatedAt: new Date().toISOString(),
    summaryPath,
    thresholdProfile: profile,
    thresholdPresetPath: presetPath,
    ok,
    checks,
  }

  fs.mkdirSync(path.dirname(gateOut), { recursive: true })
  fs.writeFileSync(gateOut, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  fs.mkdirSync(path.dirname(gateLog), { recursive: true })
  fs.appendFileSync(gateLog, `${JSON.stringify(payload)}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
  process.exitCode = ok ? 0 : 1
}

main()
