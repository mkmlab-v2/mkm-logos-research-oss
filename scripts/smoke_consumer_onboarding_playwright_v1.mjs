/**
 * Playwright E2E: mkmlife onboarding -> ask-one profile load +
 * personadiary home (/personadiary) -> ops onboarding.
 * Requires: projects/mkm/mkm-life with playwright (npm i -D playwright && npx playwright install chromium)
 *
 * Usage (workspace root):
 *   MKMLIFE_BASE_URL=http://127.0.0.1:3105 NO1KMEDI_DEV_URL=http://127.0.0.1:3010 \
 *     node scripts/smoke_consumer_onboarding_playwright_v1.mjs
 */
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const MKMLIFE_BASE = (process.env.MKMLIFE_BASE_URL || 'http://127.0.0.1:3105').replace(/\/$/, '')
const NO1KMEDI_BASE = (process.env.NO1KMEDI_DEV_URL || 'http://127.0.0.1:3010').replace(/\/$/, '')
const STRICT = process.env.MKM_SMOKE_STRICT_PLAYWRIGHT === '1'
const OUT = path.join(ROOT, 'reports', 'consumer_onboarding_playwright_smoke_v1_latest.json')

const CLINIC_ITEM_IDS = [
  'ch01', 'ch02', 'ch03', 'dg01', 'dg02', 'dg03', 'ac01', 'ac02', 'ac03', 'ms01', 'ms02', 'ms03', 'tb01', 'tb02',
]

async function loadPlaywright() {
  const candidates = [
    path.join(ROOT, 'projects', 'mkm', 'mkm-life', 'node_modules', 'playwright', 'index.mjs'),
    path.join(ROOT, 'projects', 'mkm', 'mkm-life', 'node_modules', 'playwright', 'index.js'),
  ]
  for (const candidate of candidates) {
    try {
      return await import(pathToFileURL(candidate).href)
    } catch {
      // try next
    }
  }
  try {
    return await import('playwright')
  } catch {
    return null
  }
}

async function answerClinicRadios(page, namePrefix, value = '2') {
  await page.evaluate(
    ({ prefix, ids, val }) => {
      for (const id of ids) {
        const input = document.querySelector(
          `input[type="radio"][name="${prefix}${id}"][value="${val}"]`,
        )
        if (!input) continue
        input.click()
        input.dispatchEvent(new Event('input', { bubbles: true }))
        input.dispatchEvent(new Event('change', { bubbles: true }))
      }
    },
    { prefix: namePrefix, ids: CLINIC_ITEM_IDS, val: value },
  )
  const answered = await page.locator(`input[type="radio"][name^="${namePrefix}"]:checked`).count()
  if (answered < CLINIC_ITEM_IDS.length) {
    throw new Error(`clinic_radios_incomplete:${answered}/${CLINIC_ITEM_IDS.length}`)
  }
}

async function runMkmlifeOnboarding(page) {
  const checks = []
  await page.goto(`${MKMLIFE_BASE}/onboarding`, { waitUntil: 'networkidle', timeout: 120000 })
  await page.getByRole('heading', { name: /1회 프로필|One-time profile/ }).waitFor({ timeout: 60000 })
  await page.locator('input[type="date"]').first().waitFor({ timeout: 60000 })
  await page.locator('input[type="date"]').first().fill('1990-01-15')
  await page.getByRole('button', { name: '다음' }).click()
  await page.getByText('체질 설문 (14문항)').waitFor({ timeout: 60000 })
  await answerClinicRadios(page, 'clinic-')
  const answeredBeforeSave = await page.locator('input[type="radio"][name^="clinic-"]:checked').count()
  if (answeredBeforeSave < 14) {
    throw new Error(`mkmlife_clinic_incomplete:${answeredBeforeSave}`)
  }
  await page.getByRole('button', { name: '프로필 저장' }).click()
  await page.waitForURL(/\/ask-one/, { timeout: 30000 })

  const profile = await page.evaluate(() => {
    try {
      return JSON.parse(localStorage.getItem('mkm_consumer_profile_v1') || 'null')
    } catch {
      return null
    }
  })
  checks.push({
    id: 'mkmlife_profile_saved',
    ok: profile?.onboarding_complete === true && profile?.schema === 'mkm_consumer_profile_v1',
    detail: `onboarding_complete=${profile?.onboarding_complete}`,
  })

  const responseCount = profile?.constitution?.responses
    ? Object.keys(profile.constitution.responses).length
    : 0
  checks.push({
    id: 'mkmlife_profile_14_responses',
    ok: responseCount >= 14,
    detail: `responses=${responseCount}`,
  })

  await page.locator('details.askone-context-details summary').click()
  await page.waitForFunction(
    () => {
      const birth = document.getElementById('askone-birth-time-utc')?.value || ''
      const checked = document.querySelectorAll('input[type="radio"][name^="clinic-"]:checked').length
      return birth.includes('1990-01-15') && checked >= 14
    },
    null,
    { timeout: 30000 },
  )
  const birthValue = await page.locator('#askone-birth-time-utc').inputValue()
  checks.push({
    id: 'mkmlife_askone_birth_prefill',
    ok: birthValue.includes('1990-01-15'),
    detail: `birth=${birthValue}`,
  })

  const checkedClinic = await page.locator('input[type="radio"][name^="clinic-"]:checked').count()
  checks.push({
    id: 'mkmlife_askone_clinic_prefill',
    ok: checkedClinic >= 14,
    detail: `checked=${checkedClinic}`,
  })

  return checks
}

async function readPersonadiaryOpsFromIdb(page) {
  return page.evaluate(async () => {
    const key = 'personadiary_mobile_ops_v1'
    const dbName = 'personadiary_mobile_ops_v1'
    return new Promise((resolve) => {
      const req = indexedDB.open(dbName, 2)
      req.onerror = () => resolve(null)
      req.onsuccess = () => {
        const db = req.result
        const tx = db.transaction('ops', 'readonly')
        const getReq = tx.objectStore('ops').get(key)
        getReq.onsuccess = () => resolve(getReq.result ?? null)
        getReq.onerror = () => resolve(null)
      }
    })
  })
}

async function completePersonadiaryOpsOnboardingUI(page) {
  await page.getByRole('heading', { name: '시작하기' }).waitFor({ timeout: 60000 })
  await page.locator('input[type="datetime-local"]').fill('1990-01-15T09:30')
  await page.getByRole('button', { name: '다음: 프로필 설문' }).click()
  await page.getByText('A-Code 프로필 자가체크 14문항').waitFor({ timeout: 15000 })
  await answerClinicRadios(page, 'pd-clinic-')
  await page.getByRole('button', { name: '기지 가동' }).click()
  await page.getByRole('heading', { name: '시작하기' }).waitFor({ state: 'hidden', timeout: 60000 })
}

async function runPersonadiaryHomeToOpsOnboarding(page) {
  const checks = []
  await page.goto(`${NO1KMEDI_BASE}/personadiary`, { waitUntil: 'networkidle', timeout: 120000 })

  const homeSsot = await page.locator('.pd-commercial-home-ssot').count()
  checks.push({
    id: 'personadiary_home_commercial_ssot',
    ok: homeSsot > 0,
    detail: `marker=${homeSsot > 0}`,
  })

  await page.locator('#pd-commercial-moment-title').waitFor({ timeout: 60000 })
  checks.push({
    id: 'personadiary_home_moment_section',
    ok: true,
    detail: 'visible',
  })

  await page.locator('.pd-commercial-ops-bridge a.btn-primary').click()
  await page.waitForURL(/\/personadiary\/ops/, { timeout: 30000 })
  checks.push({
    id: 'personadiary_home_ops_bridge',
    ok: true,
    detail: 'navigated=/personadiary/ops',
  })

  await completePersonadiaryOpsOnboardingUI(page)

  const ops = await readPersonadiaryOpsFromIdb(page)
  const constitution = ops?.mkm_consumer_constitution_v1
  const responseCount = constitution?.responses ? Object.keys(constitution.responses).length : 0
  checks.push({
    id: 'personadiary_ops_onboarding_complete',
    ok: constitution?.onboarding_complete === true,
    detail: `onboarding_complete=${constitution?.onboarding_complete}`,
  })
  checks.push({
    id: 'personadiary_ops_14_responses',
    ok: responseCount >= 14,
    detail: `responses=${responseCount}`,
  })
  checks.push({
    id: 'personadiary_ops_birth_saved',
    ok: Boolean(ops?.local_birth_profile_v1?.birth_instant_utc),
    detail: `birth=${ops?.local_birth_profile_v1?.birth_instant_utc ?? 'missing'}`,
  })

  return checks
}

async function runPersonadiaryOnboarding(page) {
  return runPersonadiaryHomeToOpsOnboarding(page)
}

async function main() {
  const pw = await loadPlaywright()
  if (!pw) {
    const msg = {
      schema: 'consumer_onboarding_playwright_smoke_v1',
      skipped: true,
      reason: 'playwright not installed in projects/mkm/mkm-life',
      hint: 'cd projects/mkm/mkm-life && npm i -D playwright && npx playwright install chromium',
      overall_ok: !STRICT,
    }
    console.log(JSON.stringify(msg, null, 2))
    process.exit(STRICT ? 1 : 0)
  }

  const { chromium } = pw
  const browser = await chromium.launch({ headless: true })
  const checks = []

  try {
    const mkmlifeContext = await browser.newContext()
    const mkmlifePage = await mkmlifeContext.newPage()
    try {
      checks.push(...(await runMkmlifeOnboarding(mkmlifePage)))
    } catch (err) {
      checks.push({
        id: 'mkmlife_onboarding_flow',
        ok: false,
        detail: String(err?.message || err).slice(0, 300),
      })
    } finally {
      await mkmlifeContext.close()
    }

    const pdContext = await browser.newContext()
    const pdPage = await pdContext.newPage()
    try {
      checks.push(...(await runPersonadiaryOnboarding(pdPage)))
    } catch (err) {
      checks.push({
        id: 'personadiary_onboarding_flow',
        ok: false,
        detail: String(err?.message || err).slice(0, 300),
      })
    } finally {
      await pdContext.close()
    }
  } finally {
    await browser.close()
  }

  const failed = checks.filter((c) => !c.ok)
  const out = {
    schema: 'consumer_onboarding_playwright_smoke_v1',
    generated_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    mkmlife_base: MKMLIFE_BASE,
    no1kmedi_base: NO1KMEDI_BASE,
    overall_ok: failed.length === 0,
    checks,
  }
  mkdirSync(path.dirname(OUT), { recursive: true })
  writeFileSync(OUT, `${JSON.stringify(out, null, 2)}\n`, 'utf-8')
  console.log(JSON.stringify(out, null, 2))
  process.exit(failed.length ? 1 : 0)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
