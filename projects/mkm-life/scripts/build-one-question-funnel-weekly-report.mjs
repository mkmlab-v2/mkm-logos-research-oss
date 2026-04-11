/**
 * Build 7-day trend report from funnel summary/gate logs.
 *
 * Usage:
 *   node scripts/build-one-question-funnel-weekly-report.mjs
 */

import fs from 'node:fs'
import path from 'node:path'

function readJsonl(filePath) {
  if (!fs.existsSync(filePath)) return []
  return fs
    .readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .map((line) => line.trim())
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

function toDayKey(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toISOString().slice(0, 10)
}

function avg(arr) {
  if (!arr.length) return 0
  return Number((arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(2))
}

function main() {
  const summaryLogPath = path.resolve('reports/one_question_funnel_summary_log.jsonl')
  const gateLogPath = path.resolve('reports/one_question_funnel_gate_log.jsonl')
  const actionsPath = path.resolve('reports/one_question_funnel_actions_latest.json')
  const dailyTargetsPath = path.resolve('reports/one_question_funnel_daily_targets_latest.json')
  const outJsonPath = path.resolve('reports/one_question_funnel_weekly_report_latest.json')
  const outMdPath = path.resolve('reports/one_question_funnel_weekly_report_latest.md')

  const summaryRows = readJsonl(summaryLogPath)
  const gateRows = readJsonl(gateLogPath)
  const actionsLatest = fs.existsSync(actionsPath)
    ? JSON.parse(fs.readFileSync(actionsPath, 'utf8'))
    : null
  const dailyTargetsLatest = fs.existsSync(dailyTargetsPath)
    ? JSON.parse(fs.readFileSync(dailyTargetsPath, 'utf8'))
    : null

  const now = new Date()
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)

  const summaryRecent = summaryRows.filter((r) => {
    const t = new Date(r.generatedAt || r.generated_at || 0)
    return !Number.isNaN(t.getTime()) && t >= sevenDaysAgo
  })
  const gateRecent = gateRows.filter((r) => {
    const t = new Date(r.generatedAt || r.generated_at || 0)
    return !Number.isNaN(t.getTime()) && t >= sevenDaysAgo
  })

  const dayMap = new Map()
  for (const s of summaryRecent) {
    const key = toDayKey(s.generatedAt)
    if (!key) continue
    if (!dayMap.has(key))
      dayMap.set(key, {
        queries: [],
        gatePass: [],
        chargeSuccess: [],
        evidenceOpen: [],
        addInputSubmit: [],
        addInputFollowupPass: [],
      })
    const row = dayMap.get(key)
    row.queries.push(Number(s?.events?.queryCount || 0))
    row.gatePass.push(Number(s?.kpi?.gatePassRatePct || 0))
    row.chargeSuccess.push(Number(s?.kpi?.chargeSuccessRatePct || 0))
    row.evidenceOpen.push(Number(s?.kpi?.evidenceOpenRatePct || 0))
    row.addInputSubmit.push(Number(s?.kpi?.additionalInputSubmitRatePct || 0))
    row.addInputFollowupPass.push(Number(s?.kpi?.additionalInputFollowupGatePassRatePct || 0))
  }

  const trendByDay = Array.from(dayMap.entries())
    .sort((a, b) => (a[0] < b[0] ? -1 : 1))
    .map(([day, v]) => ({
      day,
      avgQueries: avg(v.queries),
      avgGatePassRatePct: avg(v.gatePass),
      avgChargeSuccessRatePct: avg(v.chargeSuccess),
      avgEvidenceOpenRatePct: avg(v.evidenceOpen),
      avgAdditionalInputSubmitRatePct: avg(v.addInputSubmit),
      avgAdditionalInputFollowupGatePassRatePct: avg(v.addInputFollowupPass),
    }))

  const gateOkRatePct = gateRecent.length
    ? Number(((gateRecent.filter((g) => g.ok === true).length / gateRecent.length) * 100).toFixed(2))
    : 0

  const payload = {
    schema: 'one_question_funnel_weekly_report_v1',
    generatedAt: new Date().toISOString(),
    windowDays: 7,
    summaryLogPath,
    gateLogPath,
    points: {
      summary: summaryRecent.length,
      gate: gateRecent.length,
    },
    kpi: {
      gateOkRatePct,
      avgQueryCount: avg(summaryRecent.map((s) => Number(s?.events?.queryCount || 0))),
      avgGatePassRatePct: avg(summaryRecent.map((s) => Number(s?.kpi?.gatePassRatePct || 0))),
      avgChargeSuccessRatePct: avg(summaryRecent.map((s) => Number(s?.kpi?.chargeSuccessRatePct || 0))),
      avgEvidenceOpenRatePct: avg(summaryRecent.map((s) => Number(s?.kpi?.evidenceOpenRatePct || 0))),
      avgAdditionalInputSubmitRatePct: avg(
        summaryRecent.map((s) => Number(s?.kpi?.additionalInputSubmitRatePct || 0))
      ),
      avgAdditionalInputFollowupGatePassRatePct: avg(
        summaryRecent.map((s) => Number(s?.kpi?.additionalInputFollowupGatePassRatePct || 0))
      ),
    },
    latestActions: Array.isArray(actionsLatest?.actions) ? actionsLatest.actions : [],
    dailyTargetsTop: Array.isArray(dailyTargetsLatest?.top) ? dailyTargetsLatest.top : [],
    trendByDay,
  }

  const lines = []
  lines.push('# One-Question Funnel Weekly Report')
  lines.push('')
  lines.push(`- Generated at: ${payload.generatedAt}`)
  lines.push(`- Window: last ${payload.windowDays} days`)
  lines.push(`- Summary points: ${payload.points.summary}`)
  lines.push(`- Gate points: ${payload.points.gate}`)
  lines.push('')
  lines.push('## KPI Average (7d)')
  lines.push(`- Gate OK rate: ${payload.kpi.gateOkRatePct}%`)
  lines.push(`- Avg query count: ${payload.kpi.avgQueryCount}`)
  lines.push(`- Avg gate pass rate: ${payload.kpi.avgGatePassRatePct}%`)
  lines.push(`- Avg charge success rate: ${payload.kpi.avgChargeSuccessRatePct}%`)
  lines.push(`- Avg evidence open rate: ${payload.kpi.avgEvidenceOpenRatePct}%`)
  lines.push(`- Avg additional-input submit rate: ${payload.kpi.avgAdditionalInputSubmitRatePct}%`)
  lines.push(
    `- Avg additional-input follow-up gate pass rate: ${payload.kpi.avgAdditionalInputFollowupGatePassRatePct}%`
  )
  lines.push('')
  lines.push('## Daily targets (Top 3, latest run)')
  const dt = payload.dailyTargetsTop
  if (!dt.length) {
    lines.push('- No daily targets artifact; run funnel chain first.')
  } else {
    for (const t of dt) {
      const hint = t.hint ? ` | hint: ${t.hint}` : ''
      const gd = Number(t.gapDelta)
      const delta =
        t.gapDelta != null && Number.isFinite(gd)
          ? ` | gapΔ=${gd > 0 ? '+' : ''}${gd.toFixed(2)} (prev gap=${Number(t.previousGapToPass || 0).toFixed(2)})`
          : ''
      const thresh =
        t.bound === 'upper' && t.maximum != null
          ? `max≤${Number(t.maximum).toFixed(2)}`
          : `min≥${Number(t.minimum || 0).toFixed(2)}`
      lines.push(
        `- ${t.name || 'unknown'}: actual=${Number(t.actual || 0).toFixed(2)} / ${thresh} / gap=${Number(t.gapToPass || 0).toFixed(2)}${delta} | ${t.action || ''}${hint}`
      )
    }
  }
  lines.push('')
  lines.push('## Latest Recommended Actions')
  if (!payload.latestActions.length) {
    lines.push('- No required action at this time.')
  } else {
    for (const a of payload.latestActions) {
      const gap =
        a.gapToPass != null && Number.isFinite(Number(a.gapToPass))
          ? ` (gap=${Number(a.gapToPass).toFixed(2)})`
          : ''
      lines.push(`- [${a.priority || 'n/a'}] ${a.check || 'unknown'}: ${a.action || ''}${gap}`)
    }
  }
  lines.push('')
  lines.push('## Daily Trend')
  if (!trendByDay.length) {
    lines.push('- No data in the last 7 days.')
  } else {
    for (const t of trendByDay) {
      lines.push(
        `- ${t.day}: queries=${t.avgQueries}, gate=${t.avgGatePassRatePct}%, charge=${t.avgChargeSuccessRatePct}%, evidence_open=${t.avgEvidenceOpenRatePct}%, add_input_submit=${t.avgAdditionalInputSubmitRatePct}%, add_input_followup_gate=${t.avgAdditionalInputFollowupGatePassRatePct}%`
      )
    }
  }

  fs.mkdirSync(path.dirname(outJsonPath), { recursive: true })
  fs.writeFileSync(outJsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  fs.writeFileSync(outMdPath, `${lines.join('\n')}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
}

main()
