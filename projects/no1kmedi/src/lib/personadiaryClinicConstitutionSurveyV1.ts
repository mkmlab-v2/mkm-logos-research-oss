import pack from "../../public/data/clinic_constitution_survey_pack_v1.json";

export type PersonadiaryClinicSurveyItem = {
  item_id: string;
  prompt_ko: string;
  axis: string;
  core_required?: boolean;
};

export type PersonadiaryClinicSurveyPack = {
  pack_id: string;
  scale_default: { min: number; max: number; labels_ko: string[] };
  core_item_ids: string[];
  disclaimer_ko: string;
  items: PersonadiaryClinicSurveyItem[];
};

export const PERSONADIARY_CLINIC_PACK = pack as PersonadiaryClinicSurveyPack;
export const PERSONADIARY_CLINIC_PACK_ID = PERSONADIARY_CLINIC_PACK.pack_id;
export const PERSONADIARY_CLINIC_CORE_IDS = PERSONADIARY_CLINIC_PACK.core_item_ids;
export const PERSONADIARY_CLINIC_SCALE_MAX = PERSONADIARY_CLINIC_PACK.scale_default.max;
export const PERSONADIARY_CLINIC_SCALE_LABELS = PERSONADIARY_CLINIC_PACK.scale_default.labels_ko;

export function countPersonadiaryClinicAnswers(
  responses: Record<string, number | undefined>,
  itemIds?: string[],
): number {
  const ids = itemIds ?? PERSONADIARY_CLINIC_PACK.items.map((i) => i.item_id);
  return ids.filter((id) => {
    const v = responses[id];
    return typeof v === "number" && v >= 0 && v <= PERSONADIARY_CLINIC_SCALE_MAX;
  }).length;
}

export type PersonadiaryConsumerConstitutionV1 = {
  schema: "mkm_consumer_constitution_v1";
  preview_only: true;
  pack_id: string;
  responses: Record<string, number>;
  onboarding_complete: boolean;
  updated_at_utc?: string;
};

export function normalizePersonadiaryConsumerConstitution(
  raw: PersonadiaryConsumerConstitutionV1 | undefined,
): PersonadiaryConsumerConstitutionV1 | undefined {
  if (!raw || raw.schema !== "mkm_consumer_constitution_v1") return undefined;
  const responses: Record<string, number> = {};
  for (const [key, value] of Object.entries(raw.responses ?? {})) {
    if (typeof value === "number" && value >= 0 && value <= PERSONADIARY_CLINIC_SCALE_MAX) {
      responses[key] = value;
    }
  }
  return {
    schema: "mkm_consumer_constitution_v1",
    preview_only: true,
    pack_id: raw.pack_id || PERSONADIARY_CLINIC_PACK_ID,
    responses,
    onboarding_complete: raw.onboarding_complete === true,
    updated_at_utc: raw.updated_at_utc,
  };
}
