/**
 * Build gap report from latest funnel gate result.
 *
 * Usage:
 *   node scripts/build-one-question-funnel-gap-report.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function readJson(p) {
  const abs = path.isAbsolute(p) ? p : path.join(root, p)
  if (!fs.existsSync(abs)) return null
  try {
    return JSON.parse(fs.readFileSync(abs, 'utf8'))
  } catch {
    return null
  }
}

function n(v) {
  const x = Number(v)
  return Number.isFinite(x) ? x : 0
}

function round2(v) {
  return Number(n(v).toFixed(2))
}

function main() {
  const gate = readJson('reports/one_question_funnel_gate_latest.json')
  const summary = readJson('reports/one_question_funnel_summary_latest.json')

  if (!gate || !Array.isArray(gate.checks)) {
    const out = {
      schema: 'one_question_funnel_gap_report_v1',
      generatedAt: new Date().toISOString(),
      ok: false,
      reason: 'gate_artifact_missing_or_invalid',
      items: [],
    }
    const outPath = path.join(root, 'reports/one_question_funnel_gap_report_latest.json')
    fs.mkdirSync(path.dirname(outPath), { recursive: true })
    fs.writeFileSync(outPath, `${JSON.stringify(out, null, 2)}\n`, 'utf8')
    console.log(JSON.stringify(out, null, 2))
    process.exitCode = 1
    return
  }

  const items = gate.checks
    .filter((c) => c && c.pass === false)
    .map((c) => {
      const actual = n(c.actual)
      const minimum = n(c.minimum)
      const gap = round2(minimum - actual)
      return {
        name: String(c.name || 'unknown'),
        actual: round2(actual),
        minimum: round2(minimum),
        gapToPass: round2(Math.max(0, gap)),
      }
    })
    .sort((a, b) => n(b.gapToPass) - n(a.gapToPass))

  const payload = {
    schema: 'one_question_funnel_gap_report_v1',
    generatedAt: new Date().toISOString(),
    gateOk: gate.ok === true,
    thresholdProfile: gate.thresholdProfile || null,
    queryCount: n(summary?.events?.queryCount),
    items,
  }

  const outJsonPath = path.join(root, 'reports/one_question_funnel_gap_report_latest.json')
  const outMdPath = path.join(root, 'reports/one_question_funnel_gap_report_latest.md')
  fs.mkdirSync(path.dirname(outJsonPath), { recursive: true })
  fs.writeFileSync(outJsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')

  const lines = []
  lines.push('# One-Question Funnel Gap Report')
  lines.push('')
  lines.push(`- Generated at: ${payload.generatedAt}`)
  lines.push(`- Gate OK: ${payload.gateOk}`)
  lines.push(`- Threshold profile: ${payload.thresholdProfile || 'n/a'}`)
  lines.push(`- Query count: ${payload.queryCount}`)
  lines.push('')
  if (!items.length) {
    lines.push('- No gap. All gate checks passed.')
  } else {
    for (const it of items) {
      lines.push(
        `- ${it.name}: actual=${it.actual}, minimum=${it.minimum}, gap_to_pass=${it.gapToPass}`
      )
    }
  }
  fs.writeFileSync(outMdPath, `${lines.join('\n')}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
}

main()
