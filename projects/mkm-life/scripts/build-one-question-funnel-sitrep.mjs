/**
 * Build human-readable SITREP from funnel summary/gate artifacts.
 *
 * Usage:
 *   node scripts/build-one-question-funnel-sitrep.mjs
 */

import fs from 'node:fs'
import path from 'node:path'

function readJson(filePath) {
  if (!fs.existsSync(filePath)) return null
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch {
    return null
  }
}

function n(v) {
  const x = Number(v)
  return Number.isFinite(x) ? x : 0
}

function formatPct(v) {
  return `${n(v).toFixed(2)}%`
}

function main() {
  const summaryPath = path.resolve('reports/one_question_funnel_summary_latest.json')
  const gatePath = path.resolve('reports/one_question_funnel_gate_latest.json')
  const actionsPath = path.resolve('reports/one_question_funnel_actions_latest.json')
  const dailyTargetsPath = path.resolve('reports/one_question_funnel_daily_targets_latest.json')
  const outPath = path.resolve('reports/one_question_funnel_sitrep_latest.md')

  const summary = readJson(summaryPath)
  const gate = readJson(gatePath)
  const actions = readJson(actionsPath)
  const dailyTargets = readJson(dailyTargetsPath)

  const lines = []
  lines.push('# One-Question Funnel SITREP')
  lines.push('')
  lines.push(`- Generated at: ${new Date().toISOString()}`)
  lines.push(`- Summary path: \`${summaryPath}\``)
  lines.push(`- Gate path: \`${gatePath}\``)
  lines.push(`- Actions path: \`${actionsPath}\``)
  lines.push(`- Daily targets path: \`${dailyTargetsPath}\``)
  lines.push('')

  if (!summary) {
    lines.push('## Status')
    lines.push('- Summary artifact missing or invalid JSON.')
    fs.mkdirSync(path.dirname(outPath), { recursive: true })
    fs.writeFileSync(outPath, `${lines.join('\n')}\n`, 'utf8')
    console.log(lines.join('\n'))
    process.exitCode = 1
    return
  }

  const ev = summary.events || {}
  const kpi = summary.kpi || {}
  lines.push('## Event Counts')
  lines.push(`- queryCount: ${n(ev.queryCount)}`)
  lines.push(`- gateCount: ${n(ev.gateCount)}`)
  lines.push(`- chargeCount: ${n(ev.chargeCount)}`)
  lines.push(`- subscriptionViewCount: ${n(ev.subscriptionViewCount)}`)
  lines.push(`- purchaseAttemptCount: ${n(ev.purchaseAttemptCount)}`)
  lines.push(`- errorCount: ${n(ev.errorCount)}`)
  lines.push(`- evidenceOpenCount: ${n(ev.evidenceOpenCount)}`)
  lines.push(`- evidenceLinkClickCount: ${n(ev.evidenceLinkClickCount)}`)
  lines.push(`- additionalInputSubmitCount: ${n(ev.additionalInputSubmitCount)}`)
  lines.push(`- additionalInputQueryCount: ${n(ev.additionalInputQueryCount)}`)
  lines.push(`- additionalInputGateCount: ${n(ev.additionalInputGateCount)}`)
  lines.push(`- syntheticEventCount: ${n(ev.syntheticEventCount)}`)
  lines.push('')

  lines.push('## KPI')
  lines.push(`- gatePassRatePct: ${formatPct(kpi.gatePassRatePct)}`)
  lines.push(`- chargeSuccessRatePct: ${formatPct(kpi.chargeSuccessRatePct)}`)
  lines.push(
    `- subscriptionPurchaseSuccessRatePct: ${formatPct(kpi.subscriptionPurchaseSuccessRatePct)}`
  )
  lines.push(`- queryToSubscriptionViewRatePct: ${formatPct(kpi.queryToSubscriptionViewRatePct)}`)
  lines.push(`- evidenceOpenRatePct: ${formatPct(kpi.evidenceOpenRatePct)}`)
  lines.push(`- evidenceLinkClickRatePct: ${formatPct(kpi.evidenceLinkClickRatePct)}`)
  lines.push(`- additionalInputSubmitRatePct: ${formatPct(kpi.additionalInputSubmitRatePct)}`)
  lines.push(
    `- additionalInputFollowupGatePassRatePct: ${formatPct(kpi.additionalInputFollowupGatePassRatePct)}`
  )
  lines.push(`- syntheticEventRatePct: ${formatPct(kpi.syntheticEventRatePct)}`)
  lines.push(`- avgChargeAmountWon: ${n(kpi.avgChargeAmountWon).toFixed(2)}`)
  lines.push('')
  lines.push('## Data Quality')
  lines.push(`- syntheticLikely: ${summary?.dataQuality?.syntheticLikely === true}`)
  lines.push('')

  lines.push('## Gate')
  if (!gate) {
    lines.push('- Gate artifact missing or invalid JSON.')
  } else {
    lines.push(`- ok: ${gate.ok === true ? 'true' : 'false'}`)
    const checks = Array.isArray(gate.checks) ? gate.checks : []
    for (const c of checks) {
      lines.push(
        `- ${c.name}: actual=${n(c.actual).toFixed(2)} / minimum=${n(c.minimum).toFixed(2)} / pass=${c.pass === true}`
      )
    }
  }

  lines.push('')
  lines.push('## Daily Targets (Top 3)')
  if (!dailyTargets) {
    lines.push('- Daily targets artifact missing or invalid JSON.')
  } else {
    const top = Array.isArray(dailyTargets.top) ? dailyTargets.top : []
    if (!top.length) {
      lines.push('- No daily targets generated.')
    } else {
      for (const t of top) {
        const delta =
          t.gapDelta != null && Number.isFinite(n(t.gapDelta))
            ? ` | gapΔ=${n(t.gapDelta) > 0 ? '+' : ''}${n(t.gapDelta).toFixed(2)} (prev gap=${n(t.previousGapToPass).toFixed(2)})`
            : ''
        lines.push(
          `- ${t.name || 'unknown'}: actual=${n(t.actual).toFixed(2)} / target=${n(t.minimum).toFixed(2)} / gap=${n(t.gapToPass).toFixed(2)}${delta} | ${t.action || ''}`
        )
      }
    }
  }

  lines.push('')
  lines.push('## Recommended Actions')
  if (!actions) {
    lines.push('- Actions artifact missing or invalid JSON.')
  } else {
    const actionList = Array.isArray(actions.actions) ? actions.actions : []
    if (!actionList.length) {
      lines.push('- No required action at this time.')
    } else {
      for (const a of actionList) {
        lines.push(`- [${a.priority || 'n/a'}] ${a.check || 'unknown'}: ${a.action || ''}`)
      }
    }
  }

  fs.mkdirSync(path.dirname(outPath), { recursive: true })
  fs.writeFileSync(outPath, `${lines.join('\n')}\n`, 'utf8')
  console.log(lines.join('\n'))
}

main()
