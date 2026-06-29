/**
 * Playwright: clinic LOI preview reference screenshot for Figma import.
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
const PREVIEW = path.join(ROOT, 'reports/clinic_km_mmp_loi_preview_v1.html')
const OUT_JSON = path.join(ROOT, 'reports/clinic_loi_figma_reference_capture_v1_latest.json')
const SCREENSHOT = path.join(ROOT, 'reports/clinic_loi_figma_reference_screenshot_v1.png')

async function loadPlaywright() {
  try {
    const req = createRequire(path.join(MKM_LIFE, 'package.json'))
    return req('playwright')
  } catch {
    return null
  }
}

async function main() {
  const pw = await loadPlaywright()
  if (!pw) {
    const out = { schema: 'clinic_loi_figma_reference_capture_v1', skipped: true, capture_ok: false }
    await mkdir(path.dirname(OUT_JSON), { recursive: true })
    await writeFile(OUT_JSON, `${JSON.stringify(out, null, 2)}\n`, 'utf8')
    console.log(JSON.stringify(out))
    process.exit(0)
  }

  const { chromium } = pw.default ?? pw
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 720, height: 1200 } })
  try {
    await page.goto(pathToFileURL(PREVIEW).href, { waitUntil: 'networkidle', timeout: 30000 })
    await page.waitForSelector('.hero h1', { timeout: 10000 })
    await mkdir(path.dirname(SCREENSHOT), { recursive: true })
    await page.screenshot({ path: SCREENSHOT, fullPage: true })
    const wedge = await page.locator('.wedge, .hero h1').first().textContent()
    const out = {
      schema: 'clinic_loi_figma_reference_capture_v1',
      captured_at_utc: new Date().toISOString(),
      capture_ok: Boolean(wedge && wedge.includes('근거')),
      screenshot: SCREENSHOT.replace(/\\/g, '/'),
      wedge_snippet: (wedge || '').trim().slice(0, 80),
    }
    await writeFile(OUT_JSON, `${JSON.stringify(out, null, 2)}\n`, 'utf8')
    console.log(JSON.stringify({ capture_ok: out.capture_ok }))
    process.exit(out.capture_ok ? 0 : 1)
  } finally {
    await browser.close()
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
