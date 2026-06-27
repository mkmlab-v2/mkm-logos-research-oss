/**
 * PersonaDiary Design Lane local live loop: artifact sync + UI watch smoke.
 * Requires `npm run dev` on :3010.
 *
 *   npm run dev:personadiary:live
 *   → http://localhost:3010/personadiary
 */
import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const baseUrl = (process.env.NO1KMEDI_DEV_URL || 'http://127.0.0.1:3010').replace(/\/$/, '')

const children = []

function spawnWatch(name, script) {
  const child = spawn(process.execPath, [path.join(scriptDir, script)], {
    stdio: 'inherit',
    env: { ...process.env, NO1KMEDI_DEV_URL: baseUrl, FORCE_COLOR: '1' },
  })
  child.on('exit', (code) => {
    console.error(`[personadiary-live] ${name} exited ${code}`)
    for (const c of children) {
      if (c !== child && !c.killed) c.kill('SIGTERM')
    }
    process.exit(code ?? 1)
  })
  children.push(child)
  return child
}

console.log(`[personadiary-live] baseUrl=${baseUrl}`)
console.log(`[personadiary-live] open → ${baseUrl}/personadiary`)
console.log(`[personadiary-live] ops   → ${baseUrl}/personadiary/ops`)
console.log('[personadiary-live] Next.js Fast Refresh = browser hot reload on save')

spawnWatch('artifact-sync', 'watch-personadiary-artifacts-dev.mjs')
spawnWatch('ui-watch', 'watch-personadiary-dev.mjs')

process.on('SIGINT', () => {
  for (const c of children) {
    if (!c.killed) c.kill('SIGTERM')
  }
  process.exit(0)
})
