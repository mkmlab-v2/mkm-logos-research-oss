/**
 * @MKM12-METADATA
 * Type: Logic
 * Purpose: Shared personal_insight_evolution_feedback_v1 validation + JSONL append (B-track).
 */
import { appendFile, mkdir } from 'fs/promises'
import path from 'path'

export type ProductLane = 'personadiary' | 'mkmlife_one_question' | 'clinician_cdss'
export type FeedbackSurface =
  | 'daily_guide'
  | 'monthly_guide'
  | 'reflect'
  | 'one_question_report'
  | 'cds_draft'
  | 'patient_bundle'

export type PhysicianAction = 'accept' | 'edit' | 'reject' | 'defer'

export type PersonalInsightFeedbackInput = {
  productLane: ProductLane
  surface: FeedbackSurface
  helpful: boolean
  clarityScore?: number
  usefulnessScore?: number
  physicianAction?: PhysicianAction
  contentRef?: {
    profileId?: string
    questionId?: string
    requestId?: string
    calendarKst?: string
    packageSchema?: string
  }
  tags?: string[]
  freeText?: string
  consentFeedbackUse?: boolean
  probe?: boolean
}

export type PersonalInsightFeedbackEvent = {
  schema: 'personal_insight_evolution_feedback_v1'
  event_id: string
  ts_utc: string
  product_lane: ProductLane
  surface: FeedbackSurface
  helpful: boolean
  clarity_score?: number
  usefulness_score?: number
  physician_action?: PhysicianAction
  content_ref?: Record<string, string>
  tags?: string[]
  free_text?: string
  consent_feedback_use?: boolean
  probe?: boolean
  hypothesis_tier: 'B'
  non_gating: true
  preview_only: true
  research_only: true
}

const PRODUCT_LANES: ProductLane[] = ['personadiary', 'mkmlife_one_question', 'clinician_cdss']
const SURFACES: FeedbackSurface[] = [
  'daily_guide',
  'monthly_guide',
  'reflect',
  'one_question_report',
  'cds_draft',
  'patient_bundle',
]
const PHYSICIAN_ACTIONS: PhysicianAction[] = ['accept', 'edit', 'reject', 'defer']

function isScore(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= 5
}

export function validatePersonalInsightFeedback(input: PersonalInsightFeedbackInput): string | null {
  if (!PRODUCT_LANES.includes(input.productLane)) return 'product_lane_invalid'
  if (!SURFACES.includes(input.surface)) return 'surface_invalid'
  if (typeof input.helpful !== 'boolean') return 'helpful_invalid'
  if (input.clarityScore !== undefined && !isScore(input.clarityScore)) return 'clarity_score_invalid'
  if (input.usefulnessScore !== undefined && !isScore(input.usefulnessScore)) return 'usefulness_score_invalid'
  if (input.physicianAction && !PHYSICIAN_ACTIONS.includes(input.physicianAction)) {
    return 'physician_action_invalid'
  }
  if (input.freeText && input.freeText.length > 2000) return 'free_text_too_long'
  if (input.tags && (input.tags.length > 12 || input.tags.some((t) => !t.trim()))) {
    return 'tags_invalid'
  }
  return null
}

export function buildPersonalInsightFeedbackEvent(
  input: PersonalInsightFeedbackInput,
): PersonalInsightFeedbackEvent {
  const contentRef: Record<string, string> = {}
  const ref = input.contentRef
  if (ref?.profileId) contentRef.profile_id = ref.profileId.slice(0, 64)
  if (ref?.questionId) contentRef.question_id = ref.questionId.slice(0, 128)
  if (ref?.requestId) contentRef.request_id = ref.requestId.slice(0, 128)
  if (ref?.calendarKst) contentRef.calendar_kst = ref.calendarKst.slice(0, 32)
  if (ref?.packageSchema) contentRef.package_schema = ref.packageSchema.slice(0, 64)

  const event: PersonalInsightFeedbackEvent = {
    schema: 'personal_insight_evolution_feedback_v1',
    event_id: `piev1_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    ts_utc: new Date().toISOString(),
    product_lane: input.productLane,
    surface: input.surface,
    helpful: input.helpful,
    hypothesis_tier: 'B',
    non_gating: true,
    preview_only: true,
    research_only: true,
  }
  if (input.clarityScore !== undefined) event.clarity_score = input.clarityScore
  if (input.usefulnessScore !== undefined) event.usefulness_score = input.usefulnessScore
  if (input.physicianAction) event.physician_action = input.physicianAction
  if (Object.keys(contentRef).length) event.content_ref = contentRef
  if (input.tags?.length) event.tags = input.tags.map((t) => t.trim().slice(0, 32)).filter(Boolean)
  if (input.freeText?.trim()) event.free_text = input.freeText.trim().slice(0, 2000)
  if (input.consentFeedbackUse === true) event.consent_feedback_use = true
  if (input.probe === true) event.probe = true
  return event
}

export function resolvePersonalInsightAggDir(): string {
  const workspace = process.env.MKM_WORKSPACE_ROOT?.trim()
  if (workspace) {
    return path.join(workspace, 'reports', 'personal_insight_evolution')
  }
  return path.join(process.cwd(), 'reports', 'personal_insight_evolution')
}

export function laneJsonlFilename(productLane: ProductLane): string {
  if (productLane === 'personadiary') return 'personadiary_v1.jsonl'
  if (productLane === 'mkmlife_one_question') return 'mkmlife_one_question_v1.jsonl'
  return 'clinician_v1.jsonl'
}

export async function appendPersonalInsightFeedbackEvent(
  event: PersonalInsightFeedbackEvent,
): Promise<string> {
  const aggDir = process.env.PERSONAL_INSIGHT_EVOLUTION_AGG_DIR?.trim() || resolvePersonalInsightAggDir()
  await mkdir(aggDir, { recursive: true })
  const file = path.join(aggDir, laneJsonlFilename(event.product_lane))
  await appendFile(file, `${JSON.stringify(event)}\n`, 'utf8')
  return file
}
