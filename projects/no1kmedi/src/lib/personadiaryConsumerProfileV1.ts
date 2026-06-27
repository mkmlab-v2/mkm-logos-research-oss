/**
 * PersonaDiary ↔ mkm_consumer_profile_v1 local bridge (preview_only · no mkmlife API).
 */
import {
  normalizePersonadiaryConsumerConstitution,
  PERSONADIARY_CLINIC_PACK_ID,
  type PersonadiaryConsumerConstitutionV1,
} from "./personadiaryClinicConstitutionSurveyV1";
import type {
  PersonadiaryLocalBirthProfileV1,
  PersonadiaryMobileOpsV1,
} from "./personadiaryMobileOpsV1";

export const MKM_CONSUMER_PROFILE_SCHEMA = "mkm_consumer_profile_v1" as const;
export const MKM_CONSUMER_PROFILE_CACHE_KEY = "mkm_consumer_profile_v1";
export const PERSONADIARY_USER_ID_CACHE_KEY = "personadiary_user_id_v1";
export const MKM_CONSUMER_PROFILE_LANE = "consumer_survey_only" as const;

export type MkmConsumerProfileBasicV1 = {
  nickname?: string;
  birth_date?: string;
  birth_datetime?: string;
  birth_time_known?: boolean;
  gender?: "male" | "female" | "other" | "unspecified";
  iana_tz: string;
};

export type MkmConsumerConstitutionV1 = {
  pack_id: string;
  responses: Record<string, number>;
  scored_at?: string;
};

export type MkmConsumerProfileV1 = {
  schema: typeof MKM_CONSUMER_PROFILE_SCHEMA;
  user_id: string;
  basic: MkmConsumerProfileBasicV1;
  constitution: MkmConsumerConstitutionV1;
  onboarding_complete: boolean;
  lane: typeof MKM_CONSUMER_PROFILE_LANE;
  research_only: true;
  created_at: string;
  updated_at: string;
};

function canUseStorage(): boolean {
  return typeof window !== "undefined";
}

export function sanitizeConsumerUserId(raw: string): string {
  return raw.trim().replace(/[^\w.-]/g, "_").slice(0, 64);
}

export function getOrCreatePersonadiaryUserId(): string {
  if (!canUseStorage()) return "personadiary_preview";
  const existing = window.localStorage.getItem(PERSONADIARY_USER_ID_CACHE_KEY);
  if (existing) return sanitizeConsumerUserId(existing);
  const generated = `pd_${crypto.randomUUID().replace(/-/g, "").slice(0, 12)}`;
  window.localStorage.setItem(PERSONADIARY_USER_ID_CACHE_KEY, generated);
  return generated;
}

export function readCachedConsumerProfile(): MkmConsumerProfileV1 | null {
  if (!canUseStorage()) return null;
  try {
    const raw = window.localStorage.getItem(MKM_CONSUMER_PROFILE_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as MkmConsumerProfileV1;
    if (parsed?.schema !== MKM_CONSUMER_PROFILE_SCHEMA) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeCachedConsumerProfile(profile: MkmConsumerProfileV1): void {
  if (!canUseStorage()) return;
  window.localStorage.setItem(MKM_CONSUMER_PROFILE_CACHE_KEY, JSON.stringify(profile));
  window.localStorage.setItem(PERSONADIARY_USER_ID_CACHE_KEY, profile.user_id);
}

function birthDateFromInstant(iso?: string): string | undefined {
  if (!iso) return undefined;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString().slice(0, 10);
}

export function buildConsumerProfileFromOps(ops: PersonadiaryMobileOpsV1): MkmConsumerProfileV1 | null {
  const birth = ops.local_birth_profile_v1;
  const constitution = ops.mkm_consumer_constitution_v1;
  if (!birth?.updated_at_utc && !constitution?.onboarding_complete) return null;

  const userId = ops.consumer_user_id || getOrCreatePersonadiaryUserId();
  const now = new Date().toISOString();
  const cached = readCachedConsumerProfile();
  const createdAt = cached?.user_id === userId ? cached.created_at : now;

  const responses = constitution?.responses ?? {};
  const onboardingComplete =
    Boolean(constitution?.onboarding_complete) && Object.keys(responses).length > 0;

  return {
    schema: MKM_CONSUMER_PROFILE_SCHEMA,
    user_id: userId,
    basic: {
      nickname: birth?.nickname,
      birth_datetime: birth?.birth_instant_utc,
      birth_date: birthDateFromInstant(birth?.birth_instant_utc),
      birth_time_known: Boolean(birth?.birth_instant_utc),
      iana_tz: birth?.iana_tz || "Asia/Seoul",
    },
    constitution: {
      pack_id: constitution?.pack_id || PERSONADIARY_CLINIC_PACK_ID,
      responses: { ...responses },
      scored_at: constitution?.updated_at_utc,
    },
    onboarding_complete: onboardingComplete,
    lane: MKM_CONSUMER_PROFILE_LANE,
    research_only: true,
    created_at: createdAt,
    updated_at: now,
  };
}

export function syncConsumerProfileFromOps(ops: PersonadiaryMobileOpsV1): MkmConsumerProfileV1 | null {
  const profile = buildConsumerProfileFromOps(ops);
  if (!profile) return null;
  writeCachedConsumerProfile(profile);
  return profile;
}

function birthProfileFromConsumer(
  profile: MkmConsumerProfileV1
): PersonadiaryLocalBirthProfileV1 | undefined {
  const { basic } = profile;
  if (!basic.nickname && !basic.birth_datetime && !basic.birth_date) return undefined;
  const birthInstant =
    basic.birth_datetime ||
    (basic.birth_date ? `${basic.birth_date}T00:00:00.000Z` : undefined);
  return {
    schema: "local_birth_profile_v1",
    preview_only: true,
    nickname: basic.nickname,
    birth_instant_utc: birthInstant,
    iana_tz: basic.iana_tz || "Asia/Seoul",
    updated_at_utc: profile.updated_at,
  };
}

function constitutionFromConsumer(
  profile: MkmConsumerProfileV1
): PersonadiaryConsumerConstitutionV1 | undefined {
  if (!profile.onboarding_complete) return undefined;
  return normalizePersonadiaryConsumerConstitution({
    schema: "mkm_consumer_constitution_v1",
    preview_only: true,
    pack_id: profile.constitution.pack_id || PERSONADIARY_CLINIC_PACK_ID,
    responses: profile.constitution.responses,
    onboarding_complete: true,
    updated_at_utc: profile.updated_at,
  });
}

/** Reuse cached profile into ops when IDB is fresh but localStorage already has onboarding. */
export function hydrateOpsFromCachedConsumerProfile(
  ops: PersonadiaryMobileOpsV1
): PersonadiaryMobileOpsV1 {
  const cached = readCachedConsumerProfile();
  if (!cached?.onboarding_complete) return ops;

  const userId = cached.user_id || getOrCreatePersonadiaryUserId();
  const birth = ops.local_birth_profile_v1 ?? birthProfileFromConsumer(cached);
  const constitution =
    ops.mkm_consumer_constitution_v1 ?? constitutionFromConsumer(cached);

  return {
    ...ops,
    consumer_user_id: userId,
    local_birth_profile_v1: birth,
    mkm_consumer_constitution_v1: constitution,
  };
}

export function constitutionResponsesFromProfile(
  profile: MkmConsumerProfileV1 | null
): Record<string, number | undefined> {
  if (!profile?.constitution?.responses) return {};
  return { ...profile.constitution.responses };
}

/** Local survey answers for A-Code derive (preview_only · no server upload). */
export function surveyResponsesForAcodeDerive(): Record<string, number> | undefined {
  const profile = readCachedConsumerProfile();
  if (!profile?.onboarding_complete) return undefined;
  const responses = profile.constitution?.responses;
  if (!responses || !Object.keys(responses).length) return undefined;
  return { ...responses };
}
