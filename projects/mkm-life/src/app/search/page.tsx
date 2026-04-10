'use client'

import { useSearchParams, useRouter } from 'next/navigation'
import { useState, useEffect, useMemo, useRef } from 'react'
import {
  Search,
  FileText,
  Newspaper,
  ExternalLink,
  Loader2,
  BookOpen,
  ListChecks,
  Zap,
  AlertTriangle,
  HelpCircle,
} from 'lucide-react'
import type { PremiumAnswerContract } from '@/lib/premium-answer-contract'
import type { ReportSchemaV1 } from '@/lib/premium-answer-contract'
import type { ChatApiResponse } from '@/lib/chat-contract'
import type { FusionEvidenceSummaryItem } from '@/lib/jema-ai-contract'
import { getMkmLocalChatAugments } from '@/lib/mkm-local-profile'
import { formatOneQuestionGateReasonLabel } from '@/lib/one-question-quality-gate'
import { parseChatSseResponseBody } from '@/lib/parse-chat-sse'
import { trackOneQuestionFunnelEvent } from '@/lib/one-question-funnel'
import IntentPreviewLoading from '@/components/IntentPreviewLoading'
import ConfidenceBadge, { getConfidenceBucketLabel } from '@/components/ConfidenceBadge'
import EvidenceCitation from '@/components/EvidenceCitation'
import DynamicDisclaimer from '@/components/DynamicDisclaimer'

interface Source {
  id: number
  title: string
  url?: string
  year?: number
  doi?: string
  journal?: string
  source?: string
  published_at?: string
  type?: 'paper' | 'news'
}

interface BillingResult {
  charged: boolean
  chargeBlocked: boolean
  reason: string
  message?: string
  transactionId?: string
  amountWon?: number
}

/** /api/chat billing 필드 기반 — 과금 게이트(v2)와 검색 UI 연결 */
interface GateSummary {
  qualityScore: number
  chargeable: boolean
  reason: string
  policyVersion?: string
  reasonLabel: string
}

type ReportDomain = 'health' | 'finance' | 'destiny' | 'general'

function detectReportDomain(text: string): ReportDomain {
  if (/(건강|수면|피로|소화|혈압|병원|증상)/.test(text)) return 'health'
  if (/(재무|투자|매수|매도|자산|수익|돈)/.test(text)) return 'finance'
  if (/(사주|운세|운명|궁합|대운)/.test(text)) return 'destiny'
  return 'general'
}

export default function SearchPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const query = searchParams.get('q') || ''
  const streamMode = searchParams.get('stream') === '1'

  const [questionDraft, setQuestionDraft] = useState('')
  const [sources, setSources] = useState<Source[]>([])
  const [relatedQueries, setRelatedQueries] = useState<string[]>([])

  const [response, setResponse] = useState('')
  const [isLoadingResponse, setIsLoadingResponse] = useState(false)
  const [responseError, setResponseError] = useState<Error | null>(null)
  const [billingResult, setBillingResult] = useState<BillingResult | null>(null)
  const [gateSummary, setGateSummary] = useState<GateSummary | null>(null)
  const [premiumContract, setPremiumContract] = useState<PremiumAnswerContract | null>(null)
  const [reportSchemaV1, setReportSchemaV1] = useState<ReportSchemaV1 | null>(null)
  const [additionalInput, setAdditionalInput] = useState('')
  const [chargeNotice, setChargeNotice] = useState<string | null>(null)
  const [fusionEvidenceSummary, setFusionEvidenceSummary] = useState<FusionEvidenceSummaryItem[]>([])
  const seenIntentStepsRef = useRef<Set<string>>(new Set())
  const seenConfidenceBucketRef = useRef<string | null>(null)

  useEffect(() => {
    setQuestionDraft(query)
  }, [query])

  const reportDomain = useMemo<ReportDomain>(() => {
    if (query) return detectReportDomain(query)
    if (response) return detectReportDomain(response)
    return 'general'
  }, [query, response])

  useEffect(() => {
    if (!gateSummary) return
    const bucket = getConfidenceBucketLabel(gateSummary.qualityScore)
    if (seenConfidenceBucketRef.current === bucket) return
    seenConfidenceBucketRef.current = bucket
    trackOneQuestionFunnelEvent({
      event: 'confidence_badge_exposed',
      route: '/search',
      label: bucket,
      qualityScore: gateSummary.qualityScore,
      source: 'web',
    })
  }, [gateSummary])

  useEffect(() => {
    if (!response || isLoadingResponse || responseError) return
    trackOneQuestionFunnelEvent({
      event: 'disclaimer_viewed',
      route: '/search',
      label: reportDomain,
      source: 'web',
    })
  }, [response, isLoadingResponse, responseError, reportDomain])

  // API 호출로 응답 및 소스 가져오기 (`stream=1`이면 `/api/chat/stream` + parseChatSseResponseBody)
  useEffect(() => {
    if (!query) return

    const hasAdditionalInput = query.includes('추가정보:')
    trackOneQuestionFunnelEvent({
      event: 'one_question_query_received',
      route: '/search',
      label: hasAdditionalInput ? 'with_additional_input' : 'base_query',
      source: 'web',
    })

    setIsLoadingResponse(true)
    setResponseError(null)
    setGateSummary(null)
    setPremiumContract(null)
    setReportSchemaV1(null)
    setChargeNotice(null)
    setSources([])
    setBillingResult(null)

    const localAug = getMkmLocalChatAugments()
    const requestBody = JSON.stringify({
      message: query,
      ...(localAug.constitution ? { constitution: localAug.constitution } : {}),
      ...(localAug.sajuFusion ? { sajuFusion: localAug.sajuFusion } : {}),
    })

    function applyChatSuccess(
      data: {
        qualityScore: number
        chargeable: boolean
        chargeDecisionReason?: string
        billing?: ChatApiResponse['billing']
        premiumContract?: PremiumAnswerContract | null
        reportSchemaV1?: ReportSchemaV1 | null
        chargeNotice?: string | null
        response: string
        sources?: ChatApiResponse['sources']
        fusionEvidenceSummary?: unknown[]
        requestId?: string
      }
    ) {
      const br = data.billing?.reason ?? data.chargeDecisionReason ?? 'ok'
      setGateSummary({
        qualityScore: data.qualityScore,
        chargeable: data.chargeable,
        reason: br,
        policyVersion: data.billing?.policyVersion,
        reasonLabel: formatOneQuestionGateReasonLabel(br),
      })
      trackOneQuestionFunnelEvent({
        event: 'one_question_gate_decided',
        requestId: data.requestId,
        route: '/search',
        label: query.includes('추가정보:') ? 'with_additional_input' : 'base_query',
        chargeable: data.chargeable,
        qualityScore: data.qualityScore,
        reason: br,
        source: 'web',
      })
      setPremiumContract(data.premiumContract ?? null)
      setReportSchemaV1(data.reportSchemaV1 ?? null)
      setChargeNotice(typeof data.chargeNotice === 'string' ? data.chargeNotice : null)
      setResponse(data.response)
      setBillingResult(null)

      if (Array.isArray(data.fusionEvidenceSummary)) {
        setFusionEvidenceSummary(
          data.fusionEvidenceSummary
            .filter((item: any) => item && typeof item.evidence === 'string')
            .map((item: any): FusionEvidenceSummaryItem => ({
              lens: item.lens as FusionEvidenceSummaryItem['lens'],
              confidence: Number(item.confidence || 0),
              evidence: item.evidence,
            }))
        )
      } else {
        setFusionEvidenceSummary([])
      }

      if (data.billing && data.requestId) {
        const userId =
          typeof window !== 'undefined' ? localStorage.getItem('userId') || 'anonymous' : 'anonymous'
        fetch('/api/billing/charge-question', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            userId,
            requestId: data.requestId,
            billing: data.billing,
            amountWon: 1000,
          }),
        })
          .then((res) => res.json())
          .then((chargePayload) => {
            trackOneQuestionFunnelEvent({
              event: 'one_question_charge_result',
              requestId: data.requestId,
              route: '/search',
              charged: chargePayload?.charged === true,
              chargeable: data.billing?.shouldCharge === true,
              reason: String(chargePayload?.reason || 'unknown'),
              amountWon: Number(chargePayload?.amountWon || 0) || undefined,
              source: 'web',
            })
            setBillingResult({
              charged: chargePayload?.charged === true,
              chargeBlocked: chargePayload?.chargeBlocked === true,
              reason: String(chargePayload?.reason || 'unknown'),
              message: chargePayload?.message,
              transactionId: chargePayload?.transactionId,
              amountWon: chargePayload?.amountWon,
            })
          })
          .catch(() => {
            trackOneQuestionFunnelEvent({
              event: 'one_question_charge_result',
              requestId: data.requestId,
              route: '/search',
              charged: false,
              chargeable: data.billing?.shouldCharge === true,
              reason: 'charge_request_failed',
              source: 'web',
            })
            setBillingResult({
              charged: false,
              chargeBlocked: true,
              reason: 'charge_request_failed',
              message: '차감 요청 처리 중 오류가 발생했습니다.',
            })
          })
      }

      if (data.sources && Array.isArray(data.sources)) {
        setSources(
          data.sources.map((s: any, idx: number) => ({
            id: s.id || idx + 1,
            title: s.title || '제목 없음',
            url: s.url,
            year: s.year,
            doi: s.doi,
            journal: s.journal,
            source: s.source,
            published_at: s.published_at,
            type: s.source === 'pubmed_fallback' || !!s.year ? 'paper' : 'news',
          }))
        )
      }
    }

    const handleError = (err: unknown) => {
      console.error('응답 로드 실패:', err)
      trackOneQuestionFunnelEvent({
        event: 'one_question_response_error',
        route: '/search',
        success: false,
        reason: err instanceof Error ? err.message : 'unknown_error',
        source: 'web',
      })
      setResponseError(err instanceof Error ? err : new Error(String(err)))
    }

    if (streamMode) {
      fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: requestBody,
      })
        .then(async (res) => {
          const text = await res.text()
          if (!res.ok) {
            let msg = `요청 실패 (${res.status})`
            try {
              const j = JSON.parse(text) as { error?: string; hint?: string }
              if (typeof j.error === 'string') msg = j.error
              if (typeof j.hint === 'string' && j.hint) msg = `${msg}\n${j.hint}`
            } catch {
              /* raw SSE or HTML */
            }
            throw new Error(msg)
          }
          const { streamedText, done } = parseChatSseResponseBody(text)
          if (!done) {
            throw new Error('스트림 응답에 완료(done) 이벤트가 없습니다.')
          }
          applyChatSuccess({
            qualityScore: done.qualityScore,
            chargeable: done.chargeable,
            chargeDecisionReason: done.chargeDecisionReason,
            billing: done.billing,
            premiumContract: done.premiumContract ?? null,
            reportSchemaV1: done.reportSchemaV1 ?? null,
            chargeNotice: done.chargeNotice ?? null,
            response: streamedText,
            sources: done.sources,
            fusionEvidenceSummary: done.fusionEvidenceSummary,
            requestId: done.requestId,
          })
        })
        .catch(handleError)
        .finally(() => setIsLoadingResponse(false))
      return
    }

    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: requestBody,
    })
      .then(async (res) => {
        const data = (await res.json()) as Partial<ChatApiResponse> & {
          error?: string
          hint?: string
        }

        if (!res.ok) {
          const msg =
            typeof data.error === 'string' ? data.error : `요청 실패 (${res.status})`
          const hint = typeof data.hint === 'string' ? data.hint : ''
          throw new Error(hint ? `${msg}\n${hint}` : msg)
        }

        if (data.error) {
          const hint = typeof data.hint === 'string' ? data.hint : ''
          throw new Error(hint ? `${data.error}\n${hint}` : data.error)
        }

        applyChatSuccess({
          qualityScore: typeof data.qualityScore === 'number' ? data.qualityScore : 0,
          chargeable: data.chargeable === true,
          chargeDecisionReason: data.chargeDecisionReason,
          billing: data.billing,
          premiumContract: data.premiumContract ?? null,
          reportSchemaV1: data.reportSchemaV1 ?? null,
          chargeNotice: typeof data.chargeNotice === 'string' ? data.chargeNotice : null,
          response: data.response || '',
          sources: data.sources,
          fusionEvidenceSummary: data.fusionEvidenceSummary,
          requestId: data.requestId,
        })
      })
      .catch(handleError)
      .finally(() => setIsLoadingResponse(false))
  }, [query, streamMode])

  // 관련 질문 생성
  useEffect(() => {
    if (query && !isLoadingResponse) {
      // 실제로는 AI가 생성해야 하지만, 임시로 하드코딩
      setRelatedQueries([
        `${query}에 대한 최신 연구는?`,
        `${query}와 관련된 체질별 차이는?`,
        `${query}를 개선하는 실용적인 방법은?`
      ])
    }
  }, [query, isLoadingResponse])

  function handleQuestionSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = questionDraft.trim()
    if (!q) return
    const qs = new URLSearchParams()
    qs.set('q', q)
    if (streamMode) qs.set('stream', '1')
    router.push(`/search?${qs.toString()}`)
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-6 rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 p-4 md:p-5">
          <p className="text-xs font-semibold text-blue-700 mb-1">ONE-QUESTION PREMIUM REPORT</p>
          <p className="text-sm md:text-base text-gray-800">
            질문 1개를 입력하면 요약·근거·행동 중심 리포트를 제공합니다.
            품질/구조 기준을 통과한 답변에만 과금이 적용됩니다.
          </p>
        </div>

        <form
          onSubmit={handleQuestionSubmit}
          className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <div className="flex-1">
            <label htmlFor="one-q-input" className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
              원퀘스천 질문
            </label>
            <input
              id="one-q-input"
              type="text"
              value={questionDraft}
              onChange={(e) => setQuestionDraft(e.target.value)}
              placeholder="예: 태양인 체질로 야근 후 수면 리듬을 어떻게 맞추면 좋을까요?"
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
          <button
            type="submit"
            className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:from-blue-700 hover:to-indigo-700"
          >
            리포트 받기
          </button>
        </form>

        {/* Query Display */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-gray-100">
              {query || '검색 결과'}
            </h1>
          </div>
        </div>

        {/* Loading State */}
        {isLoadingResponse && (
          <div className="space-y-3 py-8">
            <div className="flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              <span className="ml-3 text-gray-600 dark:text-gray-400">AI가 답변을 생성하고 있습니다...</span>
            </div>
            <IntentPreviewLoading
              onStepSeen={(stepLabel) => {
                if (seenIntentStepsRef.current.has(stepLabel)) return
                seenIntentStepsRef.current.add(stepLabel)
                trackOneQuestionFunnelEvent({
                  event: 'intent_preview_step_seen',
                  route: '/search',
                  label: stepLabel,
                  source: 'web',
                })
              }}
            />
          </div>
        )}

        {/* Error State */}
        {responseError && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-8">
            <p className="text-red-800 dark:text-red-200 whitespace-pre-wrap">
              오류가 발생했습니다: {responseError.message}
            </p>
          </div>
        )}

        {gateSummary && !isLoadingResponse && !responseError && (
          <div
            className={`mb-6 rounded-xl border p-4 ${
              gateSummary.chargeable
                ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-800/60 dark:bg-emerald-950/30'
                : 'border-amber-200 bg-amber-50 dark:border-amber-800/60 dark:bg-amber-950/30'
            }`}
            role="status"
            aria-live="polite"
          >
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-200">
              원퀘스천 품질 게이트 ·{' '}
              {gateSummary.policyVersion || 'one-question-gate-v2'}
            </p>
            <p className="mt-1 text-sm text-slate-800 dark:text-slate-100">
              {gateSummary.reasonLabel}
            </p>
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
              품질 점수 {gateSummary.qualityScore.toFixed(2)} (기준 0.90) · 과금 적용{' '}
              {gateSummary.chargeable ? '대상' : '미적용(미과금)'}
            </p>
            <div className="mt-3">
              <ConfidenceBadge score={gateSummary.qualityScore} />
            </div>
          </div>
        )}

        {/* AI Response */}
        {response && !isLoadingResponse && (
          <div className="mb-8">
            {chargeNotice && (
              <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-800/60 dark:bg-amber-950/40">
                <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">{chargeNotice}</p>
                <p className="mt-1 text-xs text-amber-800 dark:text-amber-200/90">
                  품질·구조·안전 기준을 모두 통과하면 질문권 과금(예: 1,000원) 파이프라인으로 연결됩니다. 미통과 시 본 리포트는 참고용으로 제공됩니다.
                </p>
              </div>
            )}

            {reportSchemaV1 ? (
              <div className="space-y-4">
                <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-600 dark:bg-gray-800">
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
                    <BookOpen className="h-4 w-4 text-blue-600" aria-hidden />
                    요약
                  </h3>
                  <ul className="list-inside list-disc space-y-1 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
                    {reportSchemaV1.summary_3lines.map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                </section>
                <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-600 dark:bg-gray-800">
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
                    <ListChecks className="h-4 w-4 text-indigo-600" aria-hidden />
                    근거
                  </h3>
                  <ul className="list-inside list-disc space-y-2 text-sm text-slate-700 dark:text-slate-200">
                    {reportSchemaV1.evidence_list.map((item, i) => (
                      <li key={i}>
                        {item.rationale}
                        <EvidenceCitation
                          label={item.source_label}
                          onClick={() =>
                            trackOneQuestionFunnelEvent({
                              event: 'constitution_evidence_link_click',
                              route: '/search',
                              label: `premium_evidence_${i + 1}`,
                              source: 'web',
                            })
                          }
                        />
                      </li>
                    ))}
                  </ul>
                </section>
                <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-600 dark:bg-gray-800">
                  <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
                    <Zap className="h-4 w-4 text-amber-600" aria-hidden />
                    권장 행동
                  </h3>
                  <ul className="list-inside list-decimal space-y-2 text-sm text-slate-700 dark:text-slate-200">
                    {reportSchemaV1.action_plan_7days.map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                  </ul>
                </section>
                <section className="rounded-xl border border-orange-100 bg-orange-50/80 p-5 dark:border-orange-900/40 dark:bg-orange-950/30">
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-orange-900 dark:text-orange-100">
                    <AlertTriangle className="h-4 w-4" aria-hidden />
                    주의사항
                  </h3>
                  <p className="text-sm text-orange-950/90 dark:text-orange-100/95">{reportSchemaV1.risk_and_limitations}</p>
                </section>
                <section className="rounded-xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-600 dark:bg-slate-900/50">
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
                    <HelpCircle className="h-4 w-4 text-slate-600" aria-hidden />
                    불확실성
                  </h3>
                  <p className="text-sm text-slate-700 dark:text-slate-200">
                    {reportSchemaV1.humble_ai_message || '현재 결과는 입력 데이터 기반의 확률적 분석입니다.'}
                  </p>
                </section>
                {reportSchemaV1.confidence_bucket === 'low' && (
                  <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 dark:border-amber-900/50 dark:bg-amber-950/20">
                    <h3 className="mb-2 text-sm font-semibold text-amber-900 dark:text-amber-100">
                      추가 정보 입력 권장
                    </h3>
                    <p className="mb-3 text-sm text-amber-900/90 dark:text-amber-100/90">
                      신뢰도를 높이기 위해 현재 상태(수면/스트레스/주요 고민)를 한 줄로 더 입력해 주세요.
                    </p>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={additionalInput}
                        onChange={(e) => setAdditionalInput(e.target.value)}
                        placeholder="예: 최근 2주 평균 수면 5시간, 소화불량, 투자 손실 스트레스"
                        className="flex-1 rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-amber-500 focus:outline-none dark:border-amber-800 dark:bg-slate-900 dark:text-slate-100"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          const msg = additionalInput.trim()
                          if (!msg) return
                          trackOneQuestionFunnelEvent({
                            event: 'low_confidence_additional_input_submitted',
                            route: '/search',
                            label: reportSchemaV1.domain,
                            source: 'web',
                          })
                          const qs = new URLSearchParams()
                          qs.set('q', `${query}\n추가정보: ${msg}`)
                          if (streamMode) qs.set('stream', '1')
                          router.push(`/search?${qs.toString()}`)
                        }}
                        className="rounded-lg bg-amber-600 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-700"
                      >
                        추가정보 반영
                      </button>
                    </div>
                  </section>
                )}
                <DynamicDisclaimer domain={reportSchemaV1.domain} />
                <details className="rounded-lg border border-dashed border-gray-300 bg-white/50 p-3 text-sm dark:border-gray-600 dark:bg-gray-800/50">
                  <summary className="cursor-pointer font-medium text-gray-600 dark:text-gray-300">
                    전체 응답 텍스트 보기
                  </summary>
                  <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300">
                    {response}
                  </pre>
                </details>
              </div>
            ) : premiumContract ? (
              <div className="space-y-4">
                {/* fallback renderer for legacy contract */}
                <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-600 dark:bg-gray-800">
                  <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
                    <BookOpen className="h-4 w-4 text-blue-600" aria-hidden />
                    요약
                  </h3>
                  <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-200">{premiumContract.summary}</p>
                </section>
                <DynamicDisclaimer domain={reportDomain} />
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="prose prose-lg dark:prose-invert max-w-none">
                  <div className="whitespace-pre-wrap text-gray-900 dark:text-gray-100">
                    {response}
                  </div>
                </div>
              </div>
            )}
            {billingResult && (
              <div
                className={`mt-4 rounded-lg border p-3 text-sm ${
                  billingResult.charged
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-100'
                    : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-600 dark:bg-slate-900/40 dark:text-slate-200'
                }`}
              >
                {billingResult.charged ? (
                  <p>
                    질문권 과금 처리됨 · {billingResult.amountWon || 1000}원
                    {billingResult.transactionId ? ` · 거래 ${billingResult.transactionId}` : ''}
                  </p>
                ) : (
                  <p>
                    과금 미적용 · {billingResult.message || billingResult.reason}
                    {gateSummary && !gateSummary.chargeable
                      ? ' (품질 게이트 기준 미충족 등으로 차감 생략)'
                      : ''}
                  </p>
                )}
              </div>
            )}
            {fusionEvidenceSummary.length > 0 && (
              <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/50 dark:bg-blue-900/20">
                <h3 className="mb-2 text-sm font-semibold text-blue-800 dark:text-blue-200">융합 근거 요약</h3>
                <div className="space-y-2">
                  {fusionEvidenceSummary.map((item, idx) => (
                    <div key={`${item.lens}-${idx}`} className="text-sm text-blue-900 dark:text-blue-100">
                      <span className="font-semibold">[{item.lens}]</span>{' '}
                      <span className="text-xs opacity-80">(confidence {item.confidence.toFixed(2)})</span>{' '}
                      <span>{item.evidence}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Sources */}
        {sources.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              출처
            </h2>
            <div className="space-y-3">
              {sources.map((source) => (
                <a
                  key={source.id}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                      {source.type === 'paper' ? (
                        <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      ) : (
                        <Newspaper className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                          [{source.id}]
                        </span>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
                          {source.title}
                        </h3>
                      </div>
                      {source.year && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {source.year}년
                        </p>
                      )}
                      {source.journal && (
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                          저널: {source.journal}
                        </p>
                      )}
                      {source.source && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          출처: {source.source}
                        </p>
                      )}
                      {source.published_at && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          발행일: {source.published_at}
                        </p>
                      )}
                      {source.doi && (
                        <div className="mt-1 text-sm text-indigo-600 dark:text-indigo-400 break-all">
                          DOI: {source.doi}
                        </div>
                      )}
                      {source.url && (
                        <div className="mt-2 flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400">
                          <ExternalLink className="w-3 h-3" />
                          <span className="truncate">{source.url}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Related Queries */}
        {relatedQueries.length > 0 && (
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              관련 질문
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {relatedQueries.map((relatedQuery, index) => (
                <a
                  key={index}
                  href={
                    streamMode
                      ? `/search?q=${encodeURIComponent(relatedQuery)}&stream=1`
                      : `/search?q=${encodeURIComponent(relatedQuery)}`
                  }
                  className="block bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-md transition-all"
                >
                  <p className="text-gray-700 dark:text-gray-300">{relatedQuery}</p>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
