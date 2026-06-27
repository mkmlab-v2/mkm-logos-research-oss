/**
 * Offline smoke: PersonaDiary Logos sidebar public JSON + ops marker contract.
 * Usage: node scripts/smoke-personadiary-logos-sidebar-v1.mjs
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const jsonPath = path.join(
  root,
  'public/data/personadiary_logos_sidebar_smoke_v1_latest.json'
)
const opsPage = path.join(root, 'src/app/personadiary/ops/page.tsx')
const panel = path.join(root, 'src/components/personadiary/PersonadiaryLogosSidebarHypoPanel.tsx')

const FORBIDDEN = ['directional_hit_rate', 'sharpe', '적중률', '매수 사인']

function fail(msg) {
  console.error(`FAIL: ${msg}`)
  process.exit(1)
}

if (!fs.existsSync(jsonPath)) fail(`missing ${jsonPath}`)
const doc = JSON.parse(fs.readFileSync(jsonPath, 'utf8'))
if (doc.schema !== 'personadiary_logos_sidebar_smoke_v1') fail('schema')
if (doc.prophecy_vote !== 'none' || doc.send_gate !== 'HOLD') fail('walls')
if (!doc.sidebar_generation_ok || doc.hits?.length !== 3) fail('hits')
if (!doc.candidate_pools?.logos_ann_lite?.length) fail('candidate_pools')
if (!doc.rerank_contract?.client_local_diary) fail('rerank_contract')
const hitsBlob = JSON.stringify(doc.hits)
for (const token of FORBIDDEN) {
  if (hitsBlob.includes(token)) fail(`forbidden ${token}`)
}

const opsText = fs.readFileSync(opsPage, 'utf8')
const panelText = fs.readFileSync(panel, 'utf8')
if (!opsText.includes('pd-logos-sidebar-hypo-v1')) fail('ops marker')
if (!panelText.includes('logos_sidebar_non_gating_v1')) fail('panel contract')

console.log(
  JSON.stringify(
    {
      schema: 'personadiary_logos_sidebar_ui_smoke_v1',
      ok: true,
      json_path: 'public/data/personadiary_logos_sidebar_smoke_v1_latest.json',
      hit_count: doc.hits.length,
    },
    null,
    2
  )
)
