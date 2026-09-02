/**
 * Freeform soft-match quality gate (Done-Product ceiling, research_only).
 * No-scripture + weak lexical/embedding/fuzzy text → refuse soft *preset* route
 * (clear preset_id) over a misleading book answer.
 * Refuse ≠ hard-block (D-FREEFORM-HONEST-1): friend-floor research freeform still
 * proceeds via `logosFreeformTopicalInquiryV1` thematic bootstrap when preset is null
 * (bible-code / theology / faith / AI topical). Softmatch HTTP 422 is reserved for
 * true nonsense/empty/attack — not “missing verse number”.
 * Strong hub/verse/gospel overrides stay outside.
 */
import { hasScriptureAnchor } from "./logosInquiryQueryEnrichV1";
import {
  detectGematriaMeaningFreeformTopic,
  GEMATRIA_WRONG_PACK_PRESET_IDS,
} from "./logosInquiryVerseThematicV1";
import { isProductRiskOfftopicInquiry } from "./logosFreeformTopicalInquiryV1";
import {
  getSyncGolden200Registry,
  matchGoldenHubQuery,
} from "./logosGolden200HubMatchV1";
import { scoreQueryPresetAlignment } from "./logosStudioPresetQueryGuardV1";

export const FREEFORM_SOFTMATCH_HINT_KO =
  "등록된 성경 앵커에 확실히 연결되지 않았습니다. 권·장·구절을 포함해 구체화해 주세요. (예: 마가복음 4장 비유, 시편 23편)";

/** Alignment bar for no-scripture fuzzy text (soft keyword hits alone are not enough). */
export const FREEFORM_STRONG_TEXT_SCORE = 5;

export type FreeformSoftMatchGatePreset = {
  id: string;
  prompt_ko: string;
  keywords?: string[];
};

function normalizeQueryText(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

export function isExactPresetPromptMatch(
  query: string,
  preset: FreeformSoftMatchGatePreset,
): boolean {
  const q = normalizeQueryText(query);
  const prompt = normalizeQueryText(preset.prompt_ko || "");
  return Boolean(q && prompt && q === prompt);
}

/** Golden-200 hub override stamps must survive no-scripture softmatch gate. */
export function isGoldenHubPresetRoute(query: string, presetId: string | null | undefined): boolean {
  const id = presetId?.trim() || "";
  if (!id) return false;
  const hub = matchGoldenHubQuery(query, getSyncGolden200Registry());
  if (!hub?.preset_override_ids?.length) return false;
  return hub.preset_override_ids.some((candidate) => candidate.trim() === id);
}

function isGematriaWrongPackPresetId(presetId: string): boolean {
  if (GEMATRIA_WRONG_PACK_PRESET_IDS.has(presetId)) return true;
  // Soft-id / query_mode leftovers: genesis_8 hub, isaiah YT family, Gen.6 BigSet
  if (/^isaiah_yt/i.test(presetId)) return true;
  if (
    /genesis_8|genesis.?6|nephilim|bigset_topic_genesis|gen2_eve|inquiry_golden_hub_genesis/i.test(
      presetId,
    )
  ) {
    return true;
  }
  return false;
}

const EVE_RIB_MARKERS_RE = /하와|갈비|갈비뼈|돕는\s*배필|eve|\brib\b|tsela/i;
const GEN6_NEPHILIM_MARKERS_RE =
  /네피림|nephilim|창세기\s*6|genesis\s*6|gen\.?\s*6|하나님의\s*아들|sons\s*of\s*god/i;
const NEPHILIM_GEN6_PRESET_RE = /nephilim|gen.?6|genesis.?6|bigset_topic_nephilim/i;

/** Eve/rib + Gen.6/네피림 collision — never soft-land BigSet nephilim. */
export function isEveRibVsNephilimCollisionQuery(query: string): boolean {
  const q = query.trim();
  if (!q) return false;
  const eve =
    EVE_RIB_MARKERS_RE.test(q) || (/아담/.test(q) && /뼈|측/.test(q));
  return eve && GEN6_NEPHILIM_MARKERS_RE.test(q);
}

function isNephilimGen6PresetId(presetId: string): boolean {
  return NEPHILIM_GEN6_PRESET_RE.test(presetId.trim());
}

/**
 * True when a freeform (no scripture) soft route should be refused.
 * Strong paths kept: explicit id, scripture-anchored query, exact seed prompt,
 * high text alignment. Lexical/embedding without scripture always refuse.
 * D-PATH-G1 / D-PRESET-G1: gematria|수치의미 freeform must not soft-land Isaiah YT / Gen hubs.
 */
export function shouldRefuseFreeformSoftMatch(args: {
  query: string;
  match: string;
  preset_id: string | null | undefined;
  presets: FreeformSoftMatchGatePreset[];
}): boolean {
  const presetId = args.preset_id?.trim() || "";
  if (!presetId) return false;
  if (args.match === "id") return false;
  if (isGoldenHubPresetRoute(args.query, presetId)) return false;

  if (detectGematriaMeaningFreeformTopic(args.query) && isGematriaWrongPackPresetId(presetId)) {
    return true;
  }

  // Eve/rib vs 네피림 dual ask must not soft-land Gen.6 BigSet (오매칭).
  if (isEveRibVsNephilimCollisionQuery(args.query) && isNephilimGen6PresetId(presetId)) {
    return true;
  }

  if (hasScriptureAnchor(args.query)) return false;
  // Product-risk off-topic should always go through inquiry_offtopic_redirect bootstrap,
  // never land on a random lexical/embedding/text preset.
  if (isProductRiskOfftopicInquiry(args.query)) return true;

  if (args.match === "lexical" || args.match === "embedding") return true;

  if (args.match === "text" || args.match.startsWith("query_guard_")) {
    const preset = args.presets.find((p) => p.id === presetId);
    if (!preset) return true;
    if (isExactPresetPromptMatch(args.query, preset)) return false;
    const score = scoreQueryPresetAlignment(preset, args.query);
    return score < FREEFORM_STRONG_TEXT_SCORE;
  }

  // Unknown soft-ish match types without scripture → refuse
  if (args.match !== "none") return true;
  return false;
}

export function applyFreeformSoftMatchGate<T extends { preset_id: string | null; match: string }>(
  query: string,
  result: T,
  presets: FreeformSoftMatchGatePreset[],
): T {
  if (
    !shouldRefuseFreeformSoftMatch({
      query,
      match: result.match,
      preset_id: result.preset_id,
      presets,
    })
  ) {
    return result;
  }
  return { ...result, preset_id: null, match: "none" as T["match"] };
}
