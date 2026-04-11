/**
 * Verify funnel pipeline artifacts exist and match expected schemas (lightweight).
 *
 * Usage:
 *   node scripts/verify-one-question-funnel-operational-readiness.mjs
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

function exists(p) {
  return fs.existsSync(p)
}

function main() {
  const checks = []
  const fail = (name, detail) => checks.push({ name, pass: false, detail })
  const ok = (name, detail) => checks.push({ name, pass: true, detail })

  const paths = [
    'reports/one_question_funnel_summary_latest.json',
    'reports/one_question_funnel_gate_latest.json',
    'reports/one_question_funnel_threshold_presets_latest.json',
    'reports/one_question_funnel_threshold_refresh_latest.json',
    'reports/one_question_funnel_weekly_report_latest.json',
    'reports/one_question_funnel_actions_latest.json',
    'reports/one_question_funnel_gap_report_latest.json',
    'reports/one_question_funnel_daily_targets_latest.json',
  ]
  for (const rel of paths) {
    const p = path.join(root, rel)
    const label = `exists:${rel}`
    if (!exists(p)) fail(label, rel)
    else {
      ok(label, rel)
      const label2 = `json_valid:${rel}`
      const j = readJson(p)
      if (!j) fail(label2, rel)
      else ok(label2, rel)
    }
  }

  const mdPaths = [
    'reports/one_question_funnel_sitrep_latest.md',
    'reports/one_question_funnel_weekly_report_latest.md',
    'reports/one_question_funnel_actions_latest.md',
    'reports/one_question_funnel_gap_report_latest.md',
    'reports/one_question_funnel_daily_targets_latest.md',
  ]
  for (const rel of mdPaths) {
    const p = path.join(root, rel)
    const label = `exists:${rel}`
    if (!exists(p)) fail(label, rel)
    else ok(label, rel)
  }

  const gate = readJson(path.join(root, 'reports/one_question_funnel_gate_latest.json'))
  if (gate?.schema !== 'one_question_funnel_gate_v1') fail('gate_schema', gate?.schema || null)
  else ok('gate_schema', gate.schema)
  if (!Array.isArray(gate?.checks)) fail('gate_checks_array', false)
  else ok('gate_checks_array', true)
  if (typeof gate?.ok !== 'boolean') fail('gate_ok_boolean', typeof gate?.ok)
  else ok('gate_ok_boolean', 'boolean')

  const names = Array.isArray(gate?.checks) ? gate.checks.map((c) => c.name) : []
  const has = (n) => names.includes(n)
  if (!has('additional_input_submit_rate_pct')) fail('gate_has_additional_input_submit_check', names)
  else ok('gate_has_additional_input_submit_check', names)
  if (!has('additional_input_followup_gate_pass_rate_pct'))
    fail('gate_has_additional_input_followup_check', names)
  else ok('gate_has_additional_input_followup_check', names)

  const refresh = readJson(path.join(root, 'reports/one_question_funnel_threshold_refresh_latest.json'))
  if (refresh?.schema !== 'one_question_funnel_threshold_refresh_v1')
    fail('refresh_schema', refresh?.schema || null)
  else ok('refresh_schema', refresh.schema)
  if (typeof refresh?.shouldRefresh !== 'boolean') fail('refresh_shouldRefresh_boolean', typeof refresh?.shouldRefresh)
  else ok('refresh_shouldRefresh_boolean', 'boolean')

  const summary = readJson(path.join(root, 'reports/one_question_funnel_summary_latest.json'))
  const k = summary?.kpi || {}
  if (!('additionalInputSubmitRatePct' in k)) fail('summary_has_additional_input_submit_kpi', k)
  else ok('summary_has_additional_input_submit_kpi', k.additionalInputSubmitRatePct)
  if (!('additionalInputFollowupGatePassRatePct' in k))
    fail('summary_has_additional_input_followup_kpi', k)
  else ok('summary_has_additional_input_followup_kpi', k.additionalInputFollowupGatePassRatePct)

  const failedCount = checks.filter((c) => !c.pass).length
  const payload = {
    schema: 'one_question_funnel_operational_readiness_v1',
    generatedAt: new Date().toISOString(),
    ok: failedCount === 0,
    failedCount,
    checks,
  }

  const outPath = path.join(root, 'reports/one_question_funnel_operational_readiness_latest.json')
  fs.mkdirSync(path.dirname(outPath), { recursive: true })
  fs.writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
  process.exitCode = failedCount ? 1 : 0
}

main()
