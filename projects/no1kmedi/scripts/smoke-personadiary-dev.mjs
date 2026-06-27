/**
 * Local dev smoke: PersonaDiary /personadiary — fast gate for watch loop.
 * Usage: node scripts/smoke-personadiary-dev.mjs [baseUrl]
 */
const baseUrl = (process.argv[2] || process.env.NO1KMEDI_DEV_URL || 'http://127.0.0.1:3010').replace(
  /\/$/,
  ''
)

const PAGE_MARKERS = [
  'pd-commercial-home-v1',
  'pd-moment-nation-hero',
  'pd-moment-quota-v1',
  'pd-plus-teaser',
  '세상 속의 나',
  '찰나의 나',
  'pd-moment-grid',
  'persona-visual-card-v1',
  'preview_only',
  'Persona Diary',
]

const FORBIDDEN = ['매수 사인', '운세 확정']

async function fetchCheck(row) {
  const init = row.method === 'POST' ? { method: 'POST', headers: row.headers, body: row.body } : {}
  const res = await fetch(row.url, init)
  const text = await res.text()
  if (row.expectStatus != null && res.status !== row.expectStatus) {
    return { id: row.id, ok: false, detail: `status ${res.status} expected ${row.expectStatus}` }
  }
  if (!res.ok && row.expectStatus == null) {
    return { id: row.id, ok: false, detail: `status ${res.status}` }
  }
  if (row.expectText) {
    const missing = row.expectText.filter((m) => !text.includes(m))
    if (missing.length) {
      return { id: row.id, ok: false, detail: `missing: ${missing.join(', ')}` }
    }
  }
  const forbiddenScope = row.forbiddenScope === 'hits_only' ? '' : text
  const forbidden = FORBIDDEN.filter((m) => forbiddenScope.includes(m))
  if (forbidden.length) {
    return { id: row.id, ok: false, detail: `forbidden: ${forbidden.join(', ')}` }
  }
  if (row.expectJson) {
    let doc
    try {
      doc = JSON.parse(text)
    } catch {
      return { id: row.id, ok: false, detail: 'invalid json' }
    }
    if (!row.expectJson(doc)) {
      return { id: row.id, ok: false, detail: 'json contract failed' }
    }
  }
  return { id: row.id, ok: true, detail: `status ${res.status}` }
}

const checks = [
  {
    id: 'personadiary_page',
    url: `${baseUrl}/personadiary`,
    expectStatus: 200,
    expectText: PAGE_MARKERS,
  },
  {
    id: 'daily_guide_api',
    url: `${baseUrl}/api/personadiary/daily-guide`,
    expectJson: (d) =>
      d?.ok === true &&
      (d?.package?.schema === 'personadiary_daily_response_package_v1' ||
        d?.schema === 'personadiary_daily_response_package_v1'),
  },
  {
    id: 'moment_api',
    url: `${baseUrl}/api/personadiary/moment`,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: '오늘 점심 뭐 먹을까?', profile_id: 'commander' }),
    expectJson: (d) =>
      d?.ok === true &&
      d?.moment?.intent === 'meal' &&
      typeof d?.moment?.summary_ko === 'string' &&
      d?.moment?.moment_bundle?.schema === 'personadiary_moment_bundle_resolved_v1' &&
      typeof d?.moment?.moment_bundle?.moment_bundle_id === 'string' &&
      (d.moment.summary_ko.includes('삼계') ||
        d.moment.summary_ko.includes('국물') ||
        d.moment.summary_ko.includes('광명')),
  },
  {
    id: 'personadiary_ops_page',
    url: `${baseUrl}/personadiary/ops`,
    expectStatus: 200,
    expectText: [
      'pd-logos-sidebar-hypo-v1',
      'pd-ops-native-intent-hypo',
      'Intent 미들웨어',
      'Logos 참조 지도',
      'logos_sidebar_non_gating_v1',
      'NON_GATING',
      '내 기지',
    ],
  },
  {
    id: 'logos_sidebar_static_json',
    url: `${baseUrl}/data/personadiary_logos_sidebar_smoke_v1_latest.json`,
    forbiddenScope: 'hits_only',
    expectJson: (d) =>
      d?.schema === 'personadiary_logos_sidebar_smoke_v1' &&
      d?.prophecy_vote === 'none' &&
      d?.send_gate === 'HOLD' &&
      d?.sidebar_generation_ok === true &&
      Array.isArray(d?.hits) &&
      d.hits.length === 3 &&
      Array.isArray(d?.candidate_pools?.logos_ann_lite) &&
      d?.rerank_contract?.client_local_diary === true,
  },
]

async function main() {
  const results = []
  for (const row of checks) {
    try {
      results.push(await fetchCheck(row))
    } catch (err) {
      results.push({ id: row.id, ok: false, detail: String(err) })
    }
  }
  const overallOk = results.every((r) => r.ok)
  console.log(JSON.stringify({ schema: 'personadiary_dev_smoke_v1', baseUrl, overall_ok: overallOk, results }, null, 2))
  process.exit(overallOk ? 0 : 1)
}

main()
