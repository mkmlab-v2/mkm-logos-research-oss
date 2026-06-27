/**
 * Watch PersonaDiary UI sources; debounce-run dev smoke on save.
 * Requires `npm run dev` on :3010 (or NO1KMEDI_DEV_URL).
 *
 *   node scripts/watch-personadiary-dev.mjs [baseUrl]
 *   npm run dev:personadiary:live
 */
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(scriptDir, '..')
const baseUrl = (process.argv[2] || process.env.NO1KMEDI_DEV_URL || 'http://127.0.0.1:3010').replace(
  /\/$/,
  ''
)
const debounceMs = Number(process.env.MKM_PD_WATCH_DEBOUNCE_MS || 1200)

const WATCH_ROOTS = [
  path.join(projectRoot, 'src', 'components', 'personadiary'),
  path.join(projectRoot, 'src', 'components', 'PersonadiaryChrome.tsx'),
  path.join(projectRoot, 'src', 'app', 'personadiary'),
  path.join(projectRoot, 'src', 'content', 'personadiaryCopy.ts'),
  path.join(projectRoot, 'public', 'data'),
  path.join(projectRoot, 'src', 'app', 'globals.css'),
]

function isRelevantFile(filePath) {
  const rel = path.relative(projectRoot, filePath).replace(/\\/g, '/')
  if (rel.includes('node_modules') || rel.includes('.next/')) return false
  const ext = path.extname(filePath).toLowerCase()
  if (rel.startsWith('src/components/personadiary/')) return ['.ts', '.tsx', '.css'].includes(ext)
  if (rel === 'src/components/PersonadiaryChrome.tsx') return true
  if (rel.startsWith('src/app/personadiary/')) return ['.ts', '.tsx', '.css'].includes(ext)
  if (rel === 'src/content/personadiaryCopy.ts') return true
  if (rel.startsWith('public/data/personadiary')) return ext === '.json'
  if (rel === 'src/app/globals.css') {
    try {
      return fs.readFileSync(filePath, 'utf8').includes('.pd-')
    } catch {
      return true
    }
  }
  return false
}

let debounceTimer = null
let running = false
let pending = false

function log(msg) {
  const ts = new Date().toISOString().slice(11, 19)
  console.log(`[personadiary-watch ${ts}] ${msg}`)
}

function runNode(scriptName, args = []) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [path.join(scriptDir, scriptName), ...args], {
      cwd: projectRoot,
      stdio: 'inherit',
      shell: false,
      env: { ...process.env, FORCE_COLOR: '1' },
    })
    child.on('error', reject)
    child.on('close', (code) => {
      if (code === 0) resolve()
      else reject(new Error(`${scriptName} exit ${code}`))
    })
  })
}

async function pingDev() {
  const res = await fetch(`${baseUrl}/personadiary`, { method: 'HEAD' })
  return res.ok
}

async function runSmoke(label) {
  log(`${label} → smoke (${baseUrl}/personadiary)`)
  await runNode('smoke-personadiary-dev.mjs', [baseUrl])
  log('ok')
}

async function drainQueue() {
  if (running) {
    pending = true
    return
  }
  running = true
  try {
    do {
      pending = false
      await runSmoke('change')
    } while (pending)
  } catch (err) {
    log(`FAIL: ${err.message}`)
  } finally {
    running = false
  }
}

function scheduleSmoke(reason) {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debounceTimer = null
    void drainQueue()
  }, debounceMs)
  log(`queued (${reason})`)
}

function attachWatch(targetPath) {
  if (!fs.existsSync(targetPath)) {
    log(`skip missing: ${path.relative(projectRoot, targetPath)}`)
    return
  }
  const stat = fs.statSync(targetPath)
  if (stat.isFile()) {
    fs.watch(targetPath, () => scheduleSmoke(path.basename(targetPath)))
    log(`watch file: ${path.relative(projectRoot, targetPath)}`)
    return
  }
  fs.watch(targetPath, { recursive: true }, (_event, filename) => {
    if (!filename) return
    const full = path.join(targetPath, filename.toString())
    if (isRelevantFile(full)) scheduleSmoke(filename.toString())
  })
  log(`watch dir:  ${path.relative(projectRoot, targetPath)}`)
}

async function main() {
  log(`baseUrl=${baseUrl} debounce=${debounceMs}ms`)
  log('waiting for dev server…')
  for (let i = 0; i < 45; i++) {
    try {
      if (await pingDev()) break
    } catch {
      /* retry */
    }
    if (i === 44) {
      console.error('[personadiary-watch] dev not reachable — run: npm run dev')
      process.exit(1)
    }
    await new Promise((r) => setTimeout(r, 1000))
  }
  log('dev up')

  for (const root of WATCH_ROOTS) attachWatch(root)

  const commercialInterval = Number(process.env.MKM_PD_COMMERCIAL_VERIFY_MS || 0)
  if (commercialInterval > 0) {
    setInterval(() => {
      void runNode('verify-personadiary-live-commercial.mjs', [baseUrl]).catch((err) => {
        log(`commercial verify FAIL: ${err.message}`)
      })
    }, commercialInterval)
    log(`commercial verify every ${commercialInterval}ms`)
  }

  await drainQueue()
  log('watching — edit personadiary files; Next HMR refreshes browser (Ctrl+C to stop)')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
