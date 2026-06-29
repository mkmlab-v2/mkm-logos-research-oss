/**
 * Playwright: Trust Composition glass/blur A/B — flat vs glass panels.
 * Usage: node scripts/capture_trust_composition_glass_blur_ab_playwright_v1.mjs
 */
import { mkdir, writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = process.env.MKM_WORKSPACE_ROOT
  ? path.resolve(process.env.MKM_WORKSPACE_ROOT)
  : path.resolve(__dirname, '..')
const MKM_LIFE = path.join(ROOT, 'projects/mkm/mkm-life')
const PREVIEW = path.join(ROOT, 'reports/trust_composition_glass_blur_preview_v1.html')
const OUT_JSON = path.join(ROOT, 'reports/trust_composition_glass_blur_playwright_v1_latest.json')
const SHOT_AB = path.join(ROOT, 'reports/trust_composition_glass_blur_screenshot_ab_v1.png')
const SHOT_FLAT = path.join(ROOT, 'reports/trust_composition_glass_blur_screenshot_flat_v1.png')
const SHOT_GLASS = path.join(ROOT, 'reports/trust_composition_glass_blur_screenshot_glass_v1.png')

async function loadPlaywright() {
  try {
    const req = createRequire(path.join(MKM_LIFE, 'package.json'))
    return req('playwright')
  } catch {
    try {
      return await import('playwright')
    } catch {
      return null
    }
  }
}

async function main() {
  const pw = await loadPlaywright()
  if (!pw) {
    const out = {
      schema: 'trust_composition_glass_blur_playwright_v1',
      skipped: true,
      reason: 'playwright not installed',
      capture_ok: false,
      checks: [],
    }
    await mkdir(path.dirname(OUT_JSON), { recursive: true })
    await writeFile(OUT_JSON, `${JSON.stringify(out, null, 2)}\n`, 'utf8')
    console.log(JSON.stringify(out))
    process.exit(0)
  }

  const { chromium } = pw.default ?? pw
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 900, height: 720 } })
  const checks = []

  try {
    const fileUrl = pathToFileURL(PREVIEW).href
    await page.goto(fileUrl, { waitUntil: 'networkidle', timeout: 30000 })
    await page.waitForSelector('[data-experiment="glass_blur_v1"]', { timeout: 10000 })

    await mkdir(path.dirname(SHOT_AB), { recursive: true })
    await page.screenshot({ path: SHOT_AB, fullPage: true })

    const flat = page.locator('.panel--flat')
    const glass = page.locator('.panel--glass')
    await flat.screenshot({ path: SHOT_FLAT })
    await glass.screenshot({ path: SHOT_GLASS })

    const snap = await page.evaluate(() => {
      const text = (sel) => (document.querySelector(sel)?.textContent || '').trim()
      const flatEl = document.querySelector('.panel--flat')
      const glassEl = document.querySelector('.panel--glass')
      const glassStyle = glassEl ? getComputedStyle(glassEl) : null
      return {
        experiment: document.documentElement.getAttribute('data-experiment'),
        wedge: text('.wedge'),
        trustWedge: text('.trust-wedge'),
        flatTitle: text('.panel--flat h2'),
        glassTitle: text('.panel--glass h2'),
        glassBackdrop: glassStyle?.backdropFilter || glassStyle?.webkitBackdropFilter || '',
      }
    })

    const push = (id, ok, detail) => checks.push({ id, ok, detail })

    push('preview_experiment_attr', snap.experiment === 'glass_blur_v1', snap.experiment || '(missing)')
    push('wedge_present', snap.wedge.includes('근거 없으면'), snap.wedge)
    push('trust_wedge_present', snap.trustWedge.includes('artifact'), snap.trustWedge)
    push('flat_panel_present', snap.flatTitle.includes('Flat'), snap.flatTitle)
    push('glass_panel_present', snap.glassTitle.includes('Glass'), snap.glassTitle)
    push(
      'glass_backdrop_blur_capped',
      /blur\(/i.test(snap.glassBackdrop) && !/blur\(\s*1[3-9]|blur\(\s*[2-9]\d/i.test(snap.glassBackdrop),
      snap.glassBackdrop || '(none)',
    )
    push('screenshot_ab_written', true, SHOT_AB.replace(/\\/g, '/'))

    const captureOk = checks.every((c) => c.ok)
    const out = {
      schema: 'trust_composition_glass_blur_playwright_v1',
      captured_at_utc: new Date().toISOString(),
      preview: PREVIEW.replace(/\\/g, '/'),
      capture_ok: captureOk,
      screenshots: {
        ab: SHOT_AB.replace(/\\/g, '/'),
        flat: SHOT_FLAT.replace(/\\/g, '/'),
        glass: SHOT_GLASS.replace(/\\/g, '/'),
      },
      snap,
      checks,
    }
    await writeFile(OUT_JSON, `${JSON.stringify(out, null, 2)}\n`, 'utf8')
    console.log(JSON.stringify({ capture_ok: captureOk, out: OUT_JSON.replace(/\\/g, '/') }))
    process.exit(captureOk ? 0 : 1)
  } finally {
    await browser.close()
  }
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
