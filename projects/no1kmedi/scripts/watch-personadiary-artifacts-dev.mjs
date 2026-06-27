/**
 * Sync personadiary daily package from workspace artifact → public/data on change.
 * Requires monorepo layout: projects/no1kmedi + docs/final/artifacts at repo root.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(scriptDir, '..')
const repoRoot = path.resolve(projectRoot, '..', '..')
const SYNC_PAIRS = [
  {
    src: path.join(repoRoot, 'docs/final/artifacts/personadiary_daily_response_package_v1_latest.json'),
    dest: path.join(projectRoot, 'public/data/personadiary_daily_response_package_v1.json'),
    watchName: 'personadiary_daily_response_package',
  },
  {
    src: path.join(repoRoot, 'docs/final/artifacts/personadiary_hyper_local_poi_catalog_v1_latest.json'),
    dest: path.join(projectRoot, 'public/data/personadiary_hyper_local_poi_catalog_v1.json'),
    watchName: 'personadiary_hyper_local_poi_catalog',
  },
  {
    src: path.join(repoRoot, 'docs/final/artifacts/sasang_design_primitive_kernel_v1_latest.json'),
    dest: path.join(projectRoot, 'public/data/sasang_design_primitive_kernel_v1.json'),
    watchName: 'sasang_design_primitive_kernel',
  },
  {
    src: path.join(repoRoot, 'docs/final/artifacts/moment_bundle_pair_registry_v1_latest.json'),
    dest: path.join(projectRoot, 'public/data/moment_bundle_pair_registry_v1.json'),
    watchName: 'moment_bundle_pair_registry',
  },
]
const debounceMs = Number(process.env.MKM_PD_ARTIFACT_DEBOUNCE_MS || 800)

function log(msg) {
  const ts = new Date().toISOString().slice(11, 19)
  console.log(`[pd-artifact-sync ${ts}] ${msg}`)
}

function syncPair(pair) {
  if (!fs.existsSync(pair.src)) {
    log(`skip missing src: ${path.relative(repoRoot, pair.src)}`)
    return false
  }
  fs.mkdirSync(path.dirname(pair.dest), { recursive: true })
  const text = fs.readFileSync(pair.src, 'utf8')
  JSON.parse(text)
  if (fs.existsSync(pair.dest) && fs.readFileSync(pair.dest, 'utf8') === text) {
    return false
  }
  fs.writeFileSync(pair.dest, text, 'utf8')
  log(`wrote ${path.relative(projectRoot, pair.dest)}`)
  return true
}

function syncOnce() {
  let changed = false
  for (const pair of SYNC_PAIRS) {
    if (syncPair(pair)) changed = true
  }
  return changed
}

let timer = null

function schedule(reason) {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    timer = null
    try {
      if (syncOnce()) log(`sync ok (${reason})`)
    } catch (err) {
      log(`FAIL: ${err.message}`)
    }
  }, debounceMs)
}

const existing = SYNC_PAIRS.filter((p) => fs.existsSync(p.src))
if (!existing.length) {
  log('artifact src not found — watch disabled')
  process.exit(0)
}

syncOnce()
const watchDir = path.dirname(existing[0].src)
fs.watch(watchDir, (_e, name) => {
  if (!name) return
  const hit = SYNC_PAIRS.some((p) => String(name).includes(p.watchName))
  if (hit) schedule(String(name))
})
log(`watching ${path.relative(repoRoot, watchDir)} (${existing.length} artifacts)`)

process.on('SIGINT', () => process.exit(0))
