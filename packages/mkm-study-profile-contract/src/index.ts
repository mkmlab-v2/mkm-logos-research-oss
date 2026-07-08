/**
 * SSOT contract for MKM Study student onboarding & profile fields (v1).
 * Wire format uses snake_case; persisted app state uses camelCase (`StoredStudentProfileFieldsV1`).
 */

export type SasangType = 'soeum' | 'soyang' | 'taeeum' | 'taeyang' | 'unknown'

/** Progressive onboarding: minimal → birth → extended survey */
export type OnboardingStage = 'minimal' | 'birth_complete' | 'extended_complete'

/** Maps to advanced-consultation constitution_survey (minimal subset). */
export type ConstitutionSurveyV1 = {
  stress_response?: 'internalize' | 'externalize'
  change_preference?: 'stability' | 'challenge'
  sweat_recovery?: 'fatiguing' | 'refreshing'
}

/** Alias for HTTP JSON bodies (same keys as `schema/onboarding-request-v1.schema.json`). */
export type StudyOnboardingRequestV1 = {
  student_id: string
  grade: string
  sasang_type: SasangType
  timezone_iana?: string
  /** If false and only birth_date present, consultation uses noon-local placeholder + birth_time_unknown */
  birth_time_known?: boolean
  birth_date?: string
  birth_datetime?: string
  birth_location?: string
  gender?: 'female' | 'male' | 'unspecified'
  constitution_survey?: ConstitutionSurveyV1
  /** Shared unified pack id (canonical: mkm_constitution_survey_core_v1). The 3-field survey is its coarse proxy. */
  constitution_pack_id?: string
  /** Full 22-item responses (item_id -> 0..4), same shape as mkm_consumer_profile_v1.constitution.responses. */
  constitution_responses?: Record<string, number>
  onboarding_stage?: OnboardingStage
  myeongri_profile?: Record<string, unknown>
}

export const STUDENT_PROFILE_SCHEMA_VERSION = 'mkm_study_student_profile_v1' as const

/** Normalized profile fields persisted by apps (camelCase). */
export type StoredStudentProfileFieldsV1 = {
  schemaVersion: typeof STUDENT_PROFILE_SCHEMA_VERSION
  studentId: string
  grade: string
  onboardingStage: OnboardingStage
  sasangType: SasangType
  timezoneIana: string
  birthTimeKnown: boolean
  birthDate?: string
  birthDatetime?: string
  birthLocation?: string
  gender?: 'female' | 'male' | 'unspecified'
  constitutionSurvey?: ConstitutionSurveyV1
  /** Shared unified pack id (canonical: mkm_constitution_survey_core_v1). */
  constitutionPackId?: string
  /** Full 22-item responses (item_id -> 0..4) when promoted to extended_complete. */
  constitutionResponses?: Record<string, number>
  myeongriProfile: Record<string, unknown> | null
}

/** Default ISO-like pattern checks only — full validation stays in each stack. */
export function inferOnboardingStage(fields: {
  constitutionSurvey?: ConstitutionSurveyV1 | null
  constitutionResponses?: Record<string, number> | null
  birthDatetime?: string
  birthDate?: string
}): OnboardingStage {
  if (fields.constitutionResponses && Object.keys(fields.constitutionResponses).length > 0) {
    return 'extended_complete'
  }
  const s = fields.constitutionSurvey
  if (s?.stress_response && s?.change_preference && s?.sweat_recovery) {
    return 'extended_complete'
  }

  const hasBirth = !!(fields.birthDatetime?.trim?.() || fields.birthDate?.trim?.())
  if (hasBirth) return 'birth_complete'
  return 'minimal'
}
