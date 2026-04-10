import { test, expect } from '@playwright/test'

function mockChatPayload() {
  const premiumContract = {
    summary: 'E2E 요약: 수면 리듬은 고정 취침 시각과 햇빛 노출로 조절합니다.',
    evidence: [
      '수면 각성 주기는 광과 멜라토닌 분비와 연관됩니다.',
      '규칙적 기상이 취침 안정에 기여합니다.',
    ],
    actions: ['매일 동일 시각에 기상하기', '저녁 블루라이트 1시간 전 줄이기'],
    caution: '의학적 진단·처방은 전문의 상담이 필요합니다.',
    uncertainty: '개인차·환경에 따라 효과는 달라질 수 있습니다.',
  }
  return {
    response: `요약: ${premiumContract.summary}\n근거: ...\n권장 행동: ...`,
    sources: [] as { id: number; title: string }[],
    timestamp: new Date().toISOString(),
    ragEnabled: true,
    papersFound: 0,
    newsFound: 0,
    modelUsed: 'local:e2e-mock',
    qualityScore: 0.95,
    chargeable: true,
    chargeDecisionReason: 'ok',
    billing: {
      shouldCharge: true,
      reason: 'ok',
      qualityScore: 0.95,
      policyVersion: 'one-question-gate-v2',
    },
    metering: { sent: false, skippedReason: 'e2e_mock' },
    requestId: 'e2e-req-one-question',
    fusionPackEnabled: true,
    fusionPackChars: 10,
    contextPromptChars: 100,
    fusionEvidenceSummary: [],
    premiumContract,
    reportSchemaV1: {
      schema_version: 'report_schema_v1',
      domain: 'health',
      confidence_bucket: 'high',
      summary_3lines: [
        'E2E 요약: 수면 리듬은 고정 취침 시각과 햇빛 노출로 조절합니다.',
        '기상 시간 고정은 생체리듬 안정에 도움을 줍니다.',
        '저녁 빛 노출 감소가 수면 개시에 유리합니다.',
      ],
      evidence_list: [
        { source_label: '[1]', rationale: '수면 각성 주기는 광 자극과 연동됩니다.' },
        { source_label: '[2]', rationale: '규칙적 기상은 수면 위상 안정에 기여합니다.' },
      ],
      action_plan_7days: ['매일 동일 시각 기상', '저녁 블루라이트 노출 최소화'],
      risk_and_limitations: '개인차가 있으므로 증상이 지속되면 전문의 상담이 필요합니다.',
      humble_ai_message: '입력 데이터 기반 확률적 분석입니다.',
    },
    chargeNotice: undefined as string | undefined,
  }
}

test.describe('원퀘스천 퍼널 (모킹)', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockChatPayload()),
      })
    })
    await page.route('**/api/billing/charge-question', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          charged: false,
          chargeBlocked: true,
          reason: 'e2e_mock',
          message: 'E2E에서는 실제 차감하지 않습니다.',
        }),
      })
    })
  })

  test('홈에서 /search 진입 후 질문 제출 → 게이트·구조화 리포트 노출', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')

    const funnelLink = page.getByTestId('hero-one-question-cta')
    await expect(funnelLink).toBeVisible({ timeout: 20_000 })
    await funnelLink.scrollIntoViewIfNeeded()
    const targetHref = (await funnelLink.getAttribute('href')) || '/search'
    await funnelLink.click()
    try {
      await page.waitForURL(/\/search\/?$/, { timeout: 30_000 })
    } catch {
      // Full reload/rehydration race fallback: navigate directly to intended funnel entry.
      await page.goto(targetHref)
      await page.waitForURL(/\/search\/?$/, { timeout: 30_000 })
    }

    await page.getByLabel('원퀘스천 질문').fill('E2E 테스트 질문입니다')
    await page.getByRole('button', { name: '리포트 받기' }).click()

    await expect(page).toHaveURL(/\/search\?q=/, { timeout: 30_000 })
    await expect(page.getByText('ONE-QUESTION PREMIUM REPORT')).toBeVisible()

    await expect(page.getByRole('status')).toContainText('원퀘스천 품질 게이트')
    await expect(page.getByRole('status')).toContainText('one-question-gate-v2')

    await expect(page.getByRole('heading', { name: '요약' })).toBeVisible()
    // 본문 카드와 원문 pre 블록에 동일 문자열이 있어 strict mode 회피
    await expect(page.getByText(/E2E 요약:/).first()).toBeVisible()
    await expect(page.getByRole('heading', { name: '근거' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '권장 행동' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '주의사항' })).toBeVisible()
    await expect(page.getByRole('heading', { name: '불확실성' })).toBeVisible()

    await expect(page.getByText(/과금 미적용/)).toBeVisible()
  })
})
