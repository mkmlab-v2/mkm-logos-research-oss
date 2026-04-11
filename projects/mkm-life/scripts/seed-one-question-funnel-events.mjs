/**
 * Append synthetic funnel events to JSONL for local smoke (requestId prefix seed_req_).
 *
 * Usage:
 *   node scripts/seed-one-question-funnel-events.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function envPath(key, relDefault) {
  const v = String(process.env[key] || '').trim()
  return v ? path.resolve(v) : path.join(root, relDefault)
}

function main() {
  const outPath = envPath('FUNNEL_EVENTS_JSONL_PATH', 'reports/one_question_funnel_events.jsonl')
  if (String(process.env.RESET_SEED_FILE || '').trim() === '1' && fs.existsSync(outPath)) {
    fs.unlinkSync(outPath)
  }

  const id = () => `seed_req_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
  const at = new Date().toISOString()
  const rows = []

  const gatePassPct = Number(process.env.SEED_GATE_PASS_RATE_PCT || 80)
  const gatePassOk = (i) => (i * 7 + 3) % 100 < gatePassPct

  for (let i = 0; i < 12; i += 1) {
    const rid = id()
    rows.push({
      event: 'one_question_query_received',
      requestId: rid,
      source: 'server',
      label: 'base_query',
      at,
    })
    rows.push({
      event: 'one_question_gate_decided',
      requestId: rid,
      success: gatePassOk(i),
      label: 'base_query',
      source: 'server',
      at,
    })
    rows.push({
      event: 'one_question_charge_result',
      requestId: rid,
      success: i % 3 !== 0,
      charged: i % 3 !== 0,
      amountWon: i % 3 !== 0 ? 1000 : 0,
      source: 'server',
      at,
    })
    if (i % 4 === 0) {
      rows.push({ event: 'subscription_page_view', requestId: rid, source: 'server', at })
    }
    if (i % 5 === 0) {
      rows.push({
        event: 'subscription_purchase_result',
        requestId: rid,
        success: i % 10 !== 0,
        source: 'server',
        at,
      })
    }
    if (i % 2 === 0) {
      rows.push({ event: 'constitution_evidence_open', requestId: rid, source: 'server', at })
    }
    if (i % 3 === 0) {
      rows.push({ event: 'constitution_evidence_link_click', requestId: rid, source: 'server', at })
    }
  }

  const lowSubmit = Number(process.env.SEED_ADDITIONAL_INPUT_SUBMIT_RATE_PCT || 0)
  if (lowSubmit > 0) {
    const rid = id()
    rows.push({
      event: 'one_question_query_received',
      requestId: rid,
      label: 'with_additional_input',
      source: 'server',
      at,
    })
    rows.push({
      event: 'low_confidence_additional_input_submitted',
      requestId: rid,
      source: 'server',
      at,
    })
    rows.push({
      event: 'one_question_gate_decided',
      requestId: rid,
      success: true,
      label: 'with_additional_input',
      source: 'server',
      at,
    })
  }

  fs.mkdirSync(path.dirname(outPath), { recursive: true })
  for (const r of rows) {
    fs.appendFileSync(outPath, `${JSON.stringify(r)}\n`, 'utf8')
  }
  console.log(JSON.stringify({ ok: true, appended: rows.length, path: outPath }, null, 2))
}

main()
