/**
 * Build actionable daily targets from latest gap report.
 *
 * Usage:
 *   node scripts/build-one-question-daily-targets.mjs
 */

import fs from 'node:fs'
import path from 'node:path'

function readJson(p) {
  const abs = path.resolve(p)
  if (!fs.existsSync(abs)) return null
  try {
    return JSON.parse(fs.readFileSync(abs, 'utf8'))
  } catch {
    return null
  }
}

function n(v) {
  const x = Number(v)
  return Number.isFinite(x) ? x : 0
}

function round2(v) {
  return Number(n(v).toFixed(2))
}

function readLastJsonlObject(filePath) {
  const abs = path.resolve(filePath)
  if (!fs.existsSync(abs)) return null
  const lines = fs
    .readFileSync(abs, 'utf8')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
  if (!lines.length) return null
  try {
    return JSON.parse(lines[lines.length - 1])
  } catch {
    return null
  }
}

function targetHint(name) {
  const map = {
    query_count: '유입 채널 1개 추가 + 랜딩 CTA 상단 고정',
    charge_success_rate_pct: '결제 실패 사유 상위 1개 제거 + 재시도 UX 적용',
    subscription_purchase_success_rate_pct: '구독 CTA 문구 A/B 1회 + 결제 단계 간소화',
    query_to_subscription_view_rate_pct: '결과 카드 상단 구독 버튼 노출 강화',
    evidence_open_rate_pct: '근거 박스 기본 펼침 + 강조 배지 적용',
    additional_input_submit_rate_pct: '저신뢰 구간 입력 예시 문구 강화',
  }
  return map[name] || '담당자 확인 후 개선 실험 1개 실행'
}

function main() {
  const gap = readJson('reports/one_question_funnel_gap_report_latest.json')
  const actions = readJson('reports/one_question_funnel_actions_latest.json')
  const logPath = path.resolve('reports/one_question_funnel_daily_targets_log.jsonl')
  const outJsonPath = path.resolve('reports/one_question_funnel_daily_targets_latest.json')
  const outMdPath = path.resolve('reports/one_question_funnel_daily_targets_latest.md')

  const actionMap = new Map()
  for (const a of Array.isArray(actions?.actions) ? actions.actions : []) {
    actionMap.set(String(a.check || ''), String(a.action || ''))
  }

  const items = (Array.isArray(gap?.items) ? gap.items : [])
    .map((it) => ({
      name: String(it.name || 'unknown'),
      bound: it.bound === 'upper' ? 'upper' : 'lower',
      actual: n(it.actual),
      minimum: it.minimum != null && Number.isFinite(n(it.minimum)) ? n(it.minimum) : null,
      maximum: it.maximum != null && Number.isFinite(n(it.maximum)) ? n(it.maximum) : null,
      gapToPass: n(it.gapToPass),
      action: actionMap.get(String(it.name || '')) || targetHint(String(it.name || '')),
      hint: targetHint(String(it.name || '')),
    }))
    .sort((a, b) => b.gapToPass - a.gapToPass)

  const top = items.slice(0, 3)

  const gapsByName = Object.fromEntries(items.map((i) => [i.name, round2(i.gapToPass)]))
  const prevLog = readLastJsonlObject(logPath)
  const prevGaps =
    prevLog && typeof prevLog.gapsByName === 'object' && prevLog.gapsByName !== null
      ? prevLog.gapsByName
      : {}

  const topWithDelta = top.map((t) => {
    const prevGapRaw = prevGaps[t.name]
    const hasPrev = prevGapRaw !== undefined && Number.isFinite(n(prevGapRaw))
    const previousGapToPass = hasPrev ? round2(prevGapRaw) : null
    const gapDelta = hasPrev ? round2(t.gapToPass - n(prevGapRaw)) : null
    return { ...t, previousGapToPass, gapDelta }
  })

  const payload = {
    schema: 'one_question_funnel_daily_targets_v1',
    generatedAt: new Date().toISOString(),
    gateOk: gap?.gateOk === true,
    totalGaps: items.length,
    previousRunAt: prevLog?.generatedAt || null,
    top: topWithDelta,
  }

  const lines = []
  lines.push('# One-Question Funnel Daily Targets')
  lines.push('')
  lines.push(`- Generated at: ${payload.generatedAt}`)
  lines.push(`- Gate OK: ${payload.gateOk}`)
  lines.push(`- Total gaps: ${payload.totalGaps}`)
  lines.push('')
  if (!topWithDelta.length) {
    lines.push('- 오늘 즉시 개선이 필요한 격차 없음')
  } else {
    for (const t of topWithDelta) {
      const delta =
        t.gapDelta != null && Number.isFinite(t.gapDelta)
          ? ` | gapΔ=${t.gapDelta > 0 ? '+' : ''}${t.gapDelta} (이전 gap=${t.previousGapToPass})`
          : ''
      const thresh =
        t.bound === 'upper' && t.maximum != null ? `max≤${t.maximum}` : `min≥${t.minimum ?? 0}`
      lines.push(
        `- ${t.name}: actual=${t.actual}, ${thresh}, gap=${t.gapToPass}${delta} | action=${t.action}`
      )
    }
  }

  fs.mkdirSync(path.dirname(outJsonPath), { recursive: true })
  fs.writeFileSync(outJsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
  fs.writeFileSync(outMdPath, `${lines.join('\n')}\n`, 'utf8')

  const logLine = {
    schema: 'one_question_funnel_daily_targets_log_v1',
    generatedAt: payload.generatedAt,
    gateOk: payload.gateOk,
    gapsByName,
  }
  fs.appendFileSync(logPath, `${JSON.stringify(logLine)}\n`, 'utf8')

  console.log(JSON.stringify(payload, null, 2))
}

main()
