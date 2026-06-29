/**
 * Live smoke: app.jema-ai.com/clinician trust footer marker (Trust Composition SSR).
 */
const ORIGIN = (process.env.MKM_SMOKE_JEMA_APP_ORIGIN || 'https://app.jema-ai.com').replace(/\/$/, '')

const MARKERS = [
  'data-trust-footer="trust_composition_v1"',
  'artifact',
  '게이트',
]

async function main() {
  const url = `${ORIGIN}/clinician`
  const res = await fetch(url, { redirect: 'follow' })
  const html = await res.text()
  const missing = MARKERS.filter((m) => !html.includes(m))
  const out = {
    schema: 'jemaai_clinician_trust_footer_live_v1',
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
