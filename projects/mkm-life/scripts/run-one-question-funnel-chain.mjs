/**
 * One-question funnel daily chain:
 * 1) aggregate events -> summary
 * 2) run KPI gate -> exit code
 *
 * Usage:
 *   node scripts/run-one-question-funnel-chain.mjs
 *
 * Resolves project root (mkm-life) from this file so `reports/` paths work
 * even when invoked outside the package directory.
 */

import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
process.chdir(projectRoot)

function runNodeScript(scriptPath) {
  const abs = path.isAbsolute(scriptPath)
    ? scriptPath
    : path.join(projectRoot, scriptPath)
  const result = spawnSync(process.execPath, [abs], {
    stdio: 'inherit',
    env: process.env,
    cwd: projectRoot,
  })
  return result.status ?? 1
}

function main() {
  const aggregateStatus = runNodeScript('scripts/aggregate-one-question-funnel.mjs')
  if (aggregateStatus !== 0) {
    process.exitCode = aggregateStatus
    return
  }

  // Auto-refresh presets if enough new data/cooldown satisfied (best-effort).
  runNodeScript('scripts/auto-refresh-one-question-threshold-presets.mjs')

  const gateStatus = runNodeScript('scripts/check-one-question-funnel-gate.mjs')
  // Action recommendation is best-effort and should not overwrite gate exit code.
  runNodeScript('scripts/recommend-one-question-actions.mjs')
  // Gap report is best-effort and should not overwrite gate exit code.
  runNodeScript('scripts/build-one-question-funnel-gap-report.mjs')
  // Daily targets are best-effort and should not overwrite gate exit code.
  runNodeScript('scripts/build-one-question-daily-targets.mjs')
  // SITREP generation is best-effort and should not overwrite gate exit code.
  runNodeScript('scripts/build-one-question-funnel-sitrep.mjs')
  // Weekly trend report is best-effort and should not overwrite gate exit code.
  runNodeScript('scripts/build-one-question-funnel-weekly-report.mjs')
  // Operational readiness check is best-effort and should not overwrite gate exit code.
  runNodeScript('scripts/verify-one-question-funnel-operational-readiness.mjs')
  // Compact ops snapshot for quick monitoring (best-effort).
  runNodeScript('scripts/build-one-question-ops-snapshot.mjs')
  process.exitCode = gateStatus
}

main()
