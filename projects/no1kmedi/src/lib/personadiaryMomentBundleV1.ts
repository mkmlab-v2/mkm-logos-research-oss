/**
 * PersonaDiary moment bundle v1 — pairs design kernel state with BGM clip registry entry.
 * SSOT: docs/final/artifacts/moment_bundle_pair_registry_v1_latest.json
 */
import type { DailyGuidePackage } from "./personadiaryDailyGuide";
import {
  resolveDesignKernelForPersonadiary,
  type PathologyState,
} from "./personadiaryDesignKernelV1";
import type { MomentIntent } from "./personadiaryMoment";
import registryDoc from "../../public/data/moment_bundle_pair_registry_v1.json";

export type BgmGateDecision = "PASS" | "WARN" | "FAIL" | "NONE";
export type BgmFallback = "silent" | "tone_orb";

export type MomentBundleResolved = {
  schema: "personadiary_moment_bundle_resolved_v1";
  moment_bundle_id: string;
  registry_version: string;
  pathology_state: PathologyState;
  intent: MomentIntent;
  bgm_clip_id: string | null;
  bgm_public_href: string | null;
  bgm_gate_decision: BgmGateDecision;
  bgm_play_allowed: boolean;
  bgm_fallback: BgmFallback;
  audio_gate_report_ref: string | null;
  preview_only: true;
};

type RegistryPair = {
  moment_bundle_id: string;
  match: { pathology_state: PathologyState | "*"; intent: MomentIntent | "*" };
  bgm: {
    clip_id: string | null;
    public_href: string | null;
    gate_decision: BgmGateDecision;
    audio_gate_report_ref: string | null;
  };
};

type RegistryDoc = {
  schema: string;
  registry_version: string;
  fallback_policy: {
    on_gate_fail: BgmFallback;
    on_gate_warn: BgmFallback;
    on_missing_pair: string;
  };
  pairs: RegistryPair[];
};

const REGISTRY = registryDoc as RegistryDoc;

function pairScore(
  pair: RegistryPair,
  pathology: PathologyState,
  intent: MomentIntent
): number {
  const ps = pair.match.pathology_state;
  const it = pair.match.intent;
  if (ps === "*" && it === "*") return 0;
  let score = 0;
  if (ps === pathology) score += 2;
  else if (ps !== "*") return -1;
  if (it === intent) score += 2;
  else if (it !== "*") return -1;
  return score;
}

function findPair(
  pathology: PathologyState,
  intent: MomentIntent
): RegistryPair {
  let best: RegistryPair | null = null;
  let bestScore = -1;
  for (const pair of REGISTRY.pairs) {
    const score = pairScore(pair, pathology, intent);
    if (score > bestScore) {
      bestScore = score;
      best = pair;
    }
  }
  if (best && bestScore > 0) return best;
  const fallbackId = REGISTRY.fallback_policy.on_missing_pair;
  const fallback =
    REGISTRY.pairs.find((p) => p.moment_bundle_id === fallbackId) ||
    REGISTRY.pairs[REGISTRY.pairs.length - 1];
  return fallback;
}

function resolveFallback(decision: BgmGateDecision): BgmFallback {
  const policy = REGISTRY.fallback_policy;
  if (decision === "FAIL") return policy.on_gate_fail;
  if (decision === "WARN") return policy.on_gate_warn;
  if (decision === "NONE") return "silent";
  return "tone_orb";
}

export function resolveMomentBundle(
  pkg: DailyGuidePackage | null,
  intent: MomentIntent,
  calendarKst: string
): MomentBundleResolved {
  const kernel = resolveDesignKernelForPersonadiary(pkg, calendarKst);
  const pathology = kernel.pathology_state;
  const pair = findPair(pathology, intent);
  const decision = pair.bgm.gate_decision;
  const playAllowed = decision === "PASS" && Boolean(pair.bgm.public_href);

  return {
    schema: "personadiary_moment_bundle_resolved_v1",
    moment_bundle_id: pair.moment_bundle_id,
    registry_version: REGISTRY.registry_version,
    pathology_state: pathology,
    intent,
    bgm_clip_id: pair.bgm.clip_id,
    bgm_public_href: pair.bgm.public_href,
    bgm_gate_decision: decision,
    bgm_play_allowed: playAllowed,
    bgm_fallback: resolveFallback(decision),
    audio_gate_report_ref: pair.bgm.audio_gate_report_ref,
    preview_only: true,
  };
}
