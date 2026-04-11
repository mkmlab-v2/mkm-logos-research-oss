/**
 * Optionally re-run derive-one-question-threshold-presets when enough queries + cooldown elapsed.
 * Always writes threshold_refresh_latest.json for ops snapshot.
 */

import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
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

function hoursSince(iso) {
  const t = new Date(iso || 0).getTime()
  if (Number.isNaN(t)) return Infinity
  return (Date.now() - t) / (3600 * 1000)
}

function main() {
  const summaryPath = path.join(root, 'reports/one_question_funnel_summary_latest.json')
  const presetPath = path.join(root, 'reports/one_question_funnel_threshold_presets_latest.json')
  const outRefresh = path.join(root, 'reports/one_question_funnel_threshold_refresh_latest.json')
  const summary = readJson(summaryPath)
  const queryCount = n(summary?.events?.queryCount)
  const minQuery = n(process.env.MIN_QUERY_COUNT_FOR_PRESET_REFRESH || 50)
  const cooldownH = n(process.env.COOLDOWN_HOURS_FOR_PRESET_REFRESH || 24)

  const presetMissing = !fs.existsSync(presetPath)

  let presetGeneratedAt = null
  if (!presetMissing) {
    const st = fs.statSync(presetPath)
    presetGeneratedAt = st.mtime.toISOString()
  }
  const elapsed = presetGeneratedAt ? hoursSince(presetGeneratedAt) : Infinity

  const reasons = []
  if (!presetMissing) {
    if (queryCount < minQuery) reasons.push(`query_count_below_min(${queryCount}<${minQuery})`)
    if (elapsed < cooldownH) reasons.push(`cooldown_not_elapsed(${elapsed.toFixed(2)}h<${cooldownH}h)`)
  }

  const shouldRefresh = presetMissing || reasons.length === 0
  let refreshExitCode = 0
  if (shouldRefresh) {
    const derive = path.join(root, 'scripts/derive-one-question-threshold-presets.mjs')
    const r = spawnSync(process.execPath, [derive], { stdio: 'inherit', cwd: root, env: process.env })
    refreshExitCode = r.status ?? 1
  }

  const payload = {
    schema: 'one_question_funnel_threshold_refresh_v1',
    generatedAt: new Date().toISOString(),
    summaryPath,
    presetPath,
    queryCount,
    minQueryCount: minQuery,
    cooldownHours: cooldownH,
    elapsedHoursSincePreset: presetGeneratedAt ? Number(elapsed.toFixed(2)) : null,
    shouldRefresh,
    refreshExitCode: shouldRefresh ? refreshExitCode : 0,
    reasons,
  }

  fs.mkdirSync(path.dirname(outRefresh), { recursive: true })
  fs.writeFileSync(outRefresh, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
}

main()
