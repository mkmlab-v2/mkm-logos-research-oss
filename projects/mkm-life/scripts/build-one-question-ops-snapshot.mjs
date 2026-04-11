/**
 * Build compact ops snapshot for one-question funnel.
 *
 * Usage:
 *   node scripts/build-one-question-ops-snapshot.mjs
 */

import fs from 'node:fs'
import path from 'node:path'

function readJson(p) {
  const abs = path.resolve(p)
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

function main() {
  const summary = readJson('reports/one_question_funnel_summary_latest.json')
  const gate = readJson('reports/one_question_funnel_gate_latest.json')
  const refresh = readJson('reports/one_question_funnel_threshold_refresh_latest.json')
  const readiness = readJson('reports/one_question_funnel_operational_readiness_latest.json')
  const actions = readJson('reports/one_question_funnel_actions_latest.json')
  const gap = readJson('reports/one_question_funnel_gap_report_latest.json')
  const dailyTargets = readJson('reports/one_question_funnel_daily_targets_latest.json')

  const gapItems = Array.isArray(gap?.items) ? [...gap.items] : []
  gapItems.sort((a, b) => n(b?.gapToPass) - n(a?.gapToPass))

  const payload = {
    schema: 'one_question_funnel_ops_snapshot_v1',
    generatedAt: new Date().toISOString(),
    gate: {
      ok: gate?.ok === true,
      thresholdProfile: gate?.thresholdProfile || null,
    },
    readiness: {
      ok: readiness?.ok === true,
      failedCount: n(readiness?.failedCount),
    },
    refresh: {
      shouldRefresh: refresh?.shouldRefresh === true,
      reasons: Array.isArray(refresh?.reasons) ? refresh.reasons : [],
    },
    kpi: {
      queryCount: n(summary?.events?.queryCount),
      gatePassRatePct: n(summary?.kpi?.gatePassRatePct),
      chargeSuccessRatePct: n(summary?.kpi?.chargeSuccessRatePct),
      subscriptionPurchaseSuccessRatePct: n(summary?.kpi?.subscriptionPurchaseSuccessRatePct),
      evidenceOpenRatePct: n(summary?.kpi?.evidenceOpenRatePct),
      evidenceLinkClickRatePct: n(summary?.kpi?.evidenceLinkClickRatePct),
      additionalInputSubmitRatePct: n(summary?.kpi?.additionalInputSubmitRatePct),
      additionalInputFollowupGatePassRatePct: n(summary?.kpi?.additionalInputFollowupGatePassRatePct),
      syntheticEventRatePct: n(summary?.kpi?.syntheticEventRatePct),
    },
    dataQuality: {
      syntheticLikely: summary?.dataQuality?.syntheticLikely === true,
      syntheticEventCount: n(summary?.dataQuality?.syntheticEventCount),
      totalEvents: n(summary?.dataQuality?.totalEvents),
    },
    actions: {
      count: Array.isArray(actions?.actions) ? actions.actions.length : 0,
      top: Array.isArray(actions?.actions) ? actions.actions.slice(0, 3) : [],
    },
    gap: {
      count: gapItems.length,
      top: gapItems.slice(0, 3),
    },
    dailyTargets: {
      count: Array.isArray(dailyTargets?.top) ? dailyTargets.top.length : 0,
      previousRunAt: dailyTargets?.previousRunAt || null,
      top: Array.isArray(dailyTargets?.top) ? dailyTargets.top : [],
    },
  }

  const out = path.resolve('reports/one_question_funnel_ops_snapshot_latest.json')
  fs.mkdirSync(path.dirname(out), { recursive: true })
  fs.writeFileSync(out, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
}

main()
