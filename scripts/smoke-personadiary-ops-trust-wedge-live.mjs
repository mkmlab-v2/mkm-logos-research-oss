/**
 * Live smoke: personadiary.com/ops trust wedge (Trust Composition).
 * Usage: node scripts/smoke-personadiary-ops-trust-wedge-live.mjs
 * Env: MKM_SMOKE_PERSONADIARY_ORIGIN (default https://personadiary.com)
 */
const ORIGIN = (process.env.MKM_SMOKE_PERSONADIARY_ORIGIN || 'https://personadiary.com').replace(/\/$/, '')

const MARKERS = [
  'data-trust-wedge="trust_composition_v1"',
  'artifact',
  '게이트',
  '예측',
]

async function main() {
  const url = `${ORIGIN}/ops`
  const res = await fetch(url, { redirect: 'follow' })
  const html = await res.text()
  const missing = MARKERS.filter((m) => !html.includes(m))
  const out = {
    schema: 'personadiary_ops_trust_wedge_live_v1',
    origin: ORIGIN,
    url,
    status: res.status,
    overall_ok: res.ok && missing.length === 0,
    missing_markers: missing,
  }
  console.log(JSON.stringify(out, null, 2))
  process.exit(out.overall_ok ? 0 : 1)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
