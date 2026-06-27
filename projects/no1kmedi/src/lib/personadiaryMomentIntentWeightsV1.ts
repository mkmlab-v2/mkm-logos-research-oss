import weightsDoc from "../../public/data/personadiary_moment_intent_weights_v1.json";

export type MomentIntentFromSsot =
  | "meal"
  | "weather_fit"
  | "mood"
  | "world_me"
  | "reflect";

type WeightsDoc = {
  schema: "personadiary_moment_intent_weights_v1";
  prophecy_vote: "none";
  non_gating_sections: string[];
  intent_priority: Exclude<MomentIntentFromSsot, "reflect">[];
  intent_keywords: Record<Exclude<MomentIntentFromSsot, "reflect">, string[]>;
  intent_weights: Record<MomentIntentFromSsot, Record<string, number>>;
  section_titles_ko: Record<string, string>;
  package_required_sections: Record<MomentIntentFromSsot, string[]>;
};

const SSOT = weightsDoc as WeightsDoc;

if (SSOT.schema !== "personadiary_moment_intent_weights_v1") {
  throw new Error("personadiary_moment_intent_weights_v1 schema mismatch");
}

export const MOMENT_INTENT_WEIGHTS_SSOT = SSOT;

export const INTENT_KEYWORDS = SSOT.intent_keywords;
export const INTENT_WEIGHTS = SSOT.intent_weights;
export const INTENT_PRIORITY = SSOT.intent_priority;
export const SECTION_TITLES = SSOT.section_titles_ko;
export const NON_GATING_SECTIONS = new Set(SSOT.non_gating_sections);
export const PROPHECY_VOTE_NONE = SSOT.prophecy_vote;

export function isNonGatingSection(sectionId: string): boolean {
  return NON_GATING_SECTIONS.has(sectionId);
}
