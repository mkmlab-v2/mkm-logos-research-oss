/**
 * Live commercial UX probe — run while dev server is up.
 * Usage: node scripts/verify-personadiary-live-commercial.mjs [baseUrl]
 */
const baseUrl = (process.argv[2] || process.env.NO1KMEDI_DEV_URL || 'http://127.0.0.1:3010').replace(
  /\/$/,
  ''
)

const REQUIRED = [
  'pd-commercial-home-v1',
  'pd-moment-nation-hero',
  '세상 속의 나',
  'pd-commercial-moment',
  '찰나 질문',
  'persona-visual-card-v1',
  'design-kernel-v1',
  'moment-bundle-v1',
  'pd-plus-teaser',
  '행운·리추얼 카드',
]

const FORBIDDEN_OLD = ['홈 미리보기 · 빛의 구슬', '프리뷰 검증 축', '기지에서 하는 일']

async function main() {
  const res = await fetch(`${baseUrl}/personadiary`, { cache: 'no-store' })
  const html = await res.text()
  const missing = REQUIRED.filter((m) => !html.includes(m))
  const stale = FORBIDDEN_OLD.filter((m) => html.includes(m))
  const ok = res.ok && missing.length === 0 && stale.length === 0

  const report = {
    schema: 'personadiary_live_commercial_verify_v1',
    baseUrl,
    status: res.status,
    ok,
    missing,
    stale_markers: stale,
    hint: ok
      ? 'commercial SSR ok'
      : stale.length
        ? 'stale home HTML — restart dev server (rm .next) and hard refresh'
        : `missing: ${missing.join(', ')}`,
  }
  console.log(JSON.stringify(report, null, 2))
  process.exit(ok ? 0 : 1)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
