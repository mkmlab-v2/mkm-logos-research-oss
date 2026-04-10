import type { FusionEvidenceSummaryItem } from '@/lib/jema-ai-contract'
import type { PremiumAnswerContract, ReportSchemaV1 } from '@/lib/premium-answer-contract'

export interface ChatApiSource {
  id: number
  title: string
  url?: string
  year?: number
  doi?: string
  journal?: string
  source?: string
  published_at?: string
}

export interface ChatApiResponse {
  response: string
  sources: ChatApiSource[]
  timestamp: string
  ragEnabled: boolean
  papersFound: number
  newsFound: number
  modelUsed: string
  qualityScore: number
  chargeable: boolean
  chargeDecisionReason: string
  billing: {
    shouldCharge: boolean
    reason: string
    qualityScore: number
    policyVersion: string
  }
  metering: {
    sent: boolean
    skippedReason?: string
  }
  requestId: string
  fusionPackEnabled: boolean
  fusionPackChars: number
  contextPromptChars: number
  fusionEvidenceSummary: FusionEvidenceSummaryItem[]
  /** 구조화 리포트(프리미엄 계약 파싱). 있으면 UI에서 섹션 카드로 표시 */
  premiumContract?: PremiumAnswerContract
  /** report_schema_v1 계약. 프론트는 이 스키마를 우선 렌더링 */
  reportSchemaV1?: ReportSchemaV1
  /** 미과금 시 서버 고지 한 줄(과금 게이트 미통과 등) */
  chargeNotice?: string
}

export interface ChatStreamDonePayload {
  done: true
  modelUsed: string
  qualityScore: number
  chargeable: boolean
  chargeDecisionReason: string
  billing: ChatApiResponse['billing']
  metering: ChatApiResponse['metering']
  fusionEvidenceSummary: FusionEvidenceSummaryItem[]
  requestId: string
  fusionPackEnabled: boolean
  fusionPackChars: number
  contextPromptChars: number
  sources: ChatApiSource[]
  papersFound: number
  newsFound: number
  premiumContract?: PremiumAnswerContract
  reportSchemaV1?: ReportSchemaV1
  chargeNotice?: string
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function isChatStreamDonePayload(value: unknown): value is ChatStreamDonePayload {
  if (!isObject(value)) return false
  if (value.done !== true) return false
  if (typeof value.modelUsed !== 'string') return false
  if (typeof value.qualityScore !== 'number') return false
  if (typeof value.chargeable !== 'boolean') return false
  if (typeof value.chargeDecisionReason !== 'string') return false
  if (!isObject(value.billing)) return false
  if (!isObject(value.metering)) return false
  if (typeof value.requestId !== 'string') return false
  if (typeof value.fusionPackEnabled !== 'boolean') return false
  if (typeof value.fusionPackChars !== 'number') return false
  if (typeof value.contextPromptChars !== 'number') return false
  if (!Array.isArray(value.sources)) return false
  if (typeof value.papersFound !== 'number') return false
  if (typeof value.newsFound !== 'number') return false
  if (!Array.isArray(value.fusionEvidenceSummary)) return false
  return true
}
