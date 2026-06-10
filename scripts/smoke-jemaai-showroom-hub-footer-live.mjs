/**
 * Live smoke: jemaai.cloud showroom MKM family hub footer markers.
 * Usage: node scripts/smoke-jemaai-showroom-hub-footer-live.mjs
 * Env: MKM_SMOKE_JEMAAI_ORIGIN (default https://jemaai.cloud)
 */
const ORIGIN = process.env.MKM_SMOKE_JEMAAI_ORIGIN || 'https://jemaai.cloud'

const PAGES = [
  '/public_showroom_board_minimal.html',
  '/public_showroom_topology_radar_v1.html',
]

const MARKERS = [
  'showroom-hub-footer',
  'MKM 패밀리',
  'jema-ai.com',
  'mkmlife.com',
]

async function checkPage(path) {
  const url = `${ORIGIN}${path}`
  const res = await fetch(url)
  const html = await res.text()
  const missing = MARKERS.filter((m) => !html.includes(m))
  return {
    id: path,
    ok: res.ok && missing.length === 0,
    status: res.status,
    detail: missing.length ? `missing: ${missing.join(', ')}` : `markers ok (${MARKERS.join(', ')})`,
  }
}

const checks = await Promise.all(PAGES.map(checkPage))
const failed = checks.filter((c) => !c.ok)
const out = {
  schema: 'jemaai_showroom_hub_footer_live_v1',
  origin: ORIGIN,
  overall_ok: failed.length === 0,
  checks,
}
console.log(JSON.stringify(out, null, 2))
process.exit(failed.length ? 1 : 0)
