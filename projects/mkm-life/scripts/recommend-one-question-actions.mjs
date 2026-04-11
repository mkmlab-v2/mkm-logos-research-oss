/**
 * Recommend next actions from latest funnel gate result.
 *
 * Usage:
 *   node scripts/recommend-one-question-actions.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function readJson(filePath) {
  if (!fs.existsSync(filePath)) return null
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch {
    return null
  }
}

function buildRecommendationForCheck(check) {
  const name = String(check?.name || '')
  const pass = check?.pass === true
  const skipped = check?.skipped === true
  if (pass || skipped) return null
  const actual = Number(check?.actual || 0)
  const minimum = Number(check?.minimum || 0)
  const hasMax = check?.maximum !== undefined && Number.isFinite(Number(check.maximum))
  const maximum = hasMax ? Number(check.maximum) : null
  const gapToPass = hasMax
    ? Number(Math.max(0, actual - maximum).toFixed(2))
    : Number.isFinite(minimum - actual)
      ? Number(Math.max(0, minimum - actual).toFixed(2))
      : null

  const map = {
    query_count: '유입량 부족: 랜딩 CTA/쇼룸 배너 노출을 늘리고 일일 테스트 트래픽을 확보하세요.',
    gate_pass_rate_pct: '게이트 통과율 부족: 답변 품질 기준/프롬프트를 점검하고 차단 사유 상위를 줄이세요.',
    charge_success_rate_pct: '과금 성공률 부족: 결제 실패 사유를 분류하고 재시도/오류 메시지 UX를 개선하세요.',
    subscription_purchase_success_rate_pct:
      '구독 결제 성공률 부족: 가격/혜택 문구 A/B와 결제 단계 수를 줄이는 실험을 진행하세요.',
    query_to_subscription_view_rate_pct:
      '구독 유도율 부족: 결과 화면 내 구독 CTA 위치를 상단으로 올리고 문구를 단순화하세요.',
    evidence_open_rate_pct:
      '근거 열람률 부족: 신뢰도 안내 블록을 접힘 기본에서 펼침 기본 또는 강조 배지로 전환하세요.',
    evidence_link_click_rate_pct:
      '근거 클릭률 부족: DOI 링크를 카드형 버튼으로 바꾸고 클릭 유도 카피를 명확히 하세요.',
    additional_input_submit_rate_pct:
      '저신뢰 추가입력 유도 부족: 저신뢰 섹션을 기본 펼침으로 변경하고 입력 예시를 더 구체화하세요.',
    additional_input_followup_gate_pass_rate_pct:
      '추가입력 후 통과율 부족: 추가질문 프롬프트를 도메인별로 세분화하고 필수 입력 항목을 명시하세요.',
    synthetic_event_rate_pct:
      '실데이터 검증 필요: 시드/스모크 이벤트를 분리 보관하고 REQUIRE_REAL_DATA_GATE=1로 실행하세요.',
  }

  return {
    check: name,
    priority: 'high',
    actual: Number.isFinite(actual) ? Number(actual.toFixed(2)) : null,
    minimum: hasMax ? null : Number.isFinite(minimum) ? Number(minimum.toFixed(2)) : null,
    maximum: hasMax && Number.isFinite(maximum) ? Number(maximum.toFixed(2)) : null,
    gapToPass,
    action: map[name] || `${name} 지표 개선 액션을 정의하세요.`,
  }
}

function main() {
  const gatePath = String(process.env.FUNNEL_GATE_JSON_PATH || '').trim()
    ? path.resolve(process.env.FUNNEL_GATE_JSON_PATH)
    : path.join(root, 'reports/one_question_funnel_gate_latest.json')
  const outJsonPath = String(process.env.FUNNEL_ACTIONS_OUT_JSON_PATH || '').trim()
    ? path.resolve(process.env.FUNNEL_ACTIONS_OUT_JSON_PATH)
    : path.join(root, 'reports/one_question_funnel_actions_latest.json')
  const outMdPath = String(process.env.FUNNEL_ACTIONS_OUT_MD_PATH || '').trim()
    ? path.resolve(process.env.FUNNEL_ACTIONS_OUT_MD_PATH)
    : path.join(root, 'reports/one_question_funnel_actions_latest.md')

  const gate = readJson(gatePath)
  if (!gate) {
    const fallback = {
      schema: 'one_question_funnel_actions_v1',
      generatedAt: new Date().toISOString(),
      ok: false,
      reason: 'gate_artifact_missing',
      actions: [
        {
          check: 'gate_artifact',
          priority: 'high',
          action: '게이트 아티팩트를 먼저 생성하세요. (npm run check:one-question:funnel-chain)',
        },
      ],
    }
    fs.mkdirSync(path.dirname(outJsonPath), { recursive: true })
    fs.writeFileSync(outJsonPath, `${JSON.stringify(fallback, null, 2)}\n`, 'utf8')
    fs.writeFileSync(
      outMdPath,
      `# One-Question Funnel Actions\n\n- Gate artifact missing.\n- Run \`npm run -s check:one-question:funnel-chain\` first.\n`,
      'utf8'
    )
    console.log(JSON.stringify(fallback, null, 2))
    process.exitCode = 1
    return
  }

  const checks = Array.isArray(gate.checks) ? gate.checks : []
  const actions = checks
    .map(buildRecommendationForCheck)
    .filter(Boolean)
    .sort((a, b) => {
      const ga = Number.isFinite(a?.gapToPass) ? Number(a.gapToPass) : -1
      const gb = Number.isFinite(b?.gapToPass) ? Number(b.gapToPass) : -1
      return gb - ga
    })

  const payload = {
    schema: 'one_question_funnel_actions_v1',
    generatedAt: new Date().toISOString(),
    ok: gate.ok === true,
    thresholdProfile: gate.thresholdProfile || null,
    actions,
  }

  const lines = []
  lines.push('# One-Question Funnel Actions')
  lines.push('')
  lines.push(`- Generated at: ${payload.generatedAt}`)
  lines.push(`- Gate OK: ${payload.ok}`)
  lines.push(`- Threshold profile: ${payload.thresholdProfile || 'n/a'}`)
  lines.push('')
  if (!actions.length) {
    lines.push('- 현재 필수 액션 없음 (모든 체크 통과 또는 샘플 가드 스킵).')
  } else {
    for (const a of actions) {
      const band =
        a.maximum != null && Number.isFinite(Number(a.maximum))
          ? `maximum=${a.maximum}`
          : `minimum=${a.minimum}`
      lines.push(
        `- [${a.priority}] ${a.check}: ${a.action} (actual=${a.actual}, ${band}, gap=${a.gapToPass})`
      )
    }
  }

  fs.mkdirSync(path.dirname(outJsonPath), { recursive: true })
  fs.writeFileSync(outJsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  fs.writeFileSync(outMdPath, `${lines.join('\n')}\n`, 'utf8')
  console.log(JSON.stringify(payload, null, 2))
}

main()
