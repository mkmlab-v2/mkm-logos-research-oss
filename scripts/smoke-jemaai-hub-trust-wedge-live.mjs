/**
 * Live smoke: jema-ai.com /hub trust wedge (Trust Composition).
 * Usage: node scripts/smoke-jemaai-hub-trust-wedge-live.mjs
 * Env: MKM_SMOKE_JEMA_ORIGIN (default https://jema-ai.com)
 */
const ORIGIN = (process.env.MKM_SMOKE_JEMA_ORIGIN || 'https://jema-ai.com').replace(/\/$/, '')

const MARKERS = [
  'universe-hub-ask-trust-wedge',
  'artifact',
  '게이트',
]

async function main() {
  const url = `${ORIGIN}/hub`
  const res = await fetch(url, { redirect: 'follow' })
  const html = await res.text()
  const missing = MARKERS.filter((m) => !html.includes(m))
  const out = {
    schema: 'jemaai_hub_trust_wedge_live_v1',
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
