/**
 * Remove synthetic rows (requestId seed_req_*) from funnel JSONL; archive seeds to a side file.
 *
 * Usage:
 *   node scripts/reset-one-question-funnel-realdata.mjs
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
  const mainPath = envPath('FUNNEL_EVENTS_JSONL_PATH', 'reports/one_question_funnel_events.jsonl')
  if (!fs.existsSync(mainPath)) {
    console.log(JSON.stringify({ ok: true, reason: 'no_event_file', path: mainPath }, null, 2))
    return
  }
  const raw = fs.readFileSync(mainPath, 'utf8')
  const lines = raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  const synthetic = []
  const real = []
  for (const line of lines) {
    let row
    try {
      row = JSON.parse(line)
    } catch {
      continue
    }
    const id = String(row?.requestId || '')
    if (id.startsWith('seed_req_')) synthetic.push(line)
    else real.push(line)
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, '-')
  const archivePath = path.join(
    path.dirname(mainPath),
    `one_question_funnel_events_synthetic_archived_${stamp}.jsonl`
  )
  if (synthetic.length) {
    fs.writeFileSync(archivePath, `${synthetic.join('\n')}\n`, 'utf8')
  }
  const backupPath = `${mainPath}.bak_${stamp}`
  fs.copyFileSync(mainPath, backupPath)
  fs.writeFileSync(mainPath, real.length ? `${real.join('\n')}\n` : '', 'utf8')

  console.log(
    JSON.stringify(
      {
        ok: true,
        mainPath,
        backupPath,
        archivePath: synthetic.length ? archivePath : null,
        removedSynthetic: synthetic.length,
        remainingReal: real.length,
      },
      null,
      2
    )
  )
}

main()
