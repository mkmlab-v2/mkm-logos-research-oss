/**
 * PersonaDiary design kernel v1 — resolves sasang primitive kernel → UI params.
 * SSOT charter: docs/final/MKM_DESIGN_PHILOSOPHY_CONSTITUTION_V1.md
 */
import type { DailyGuidePackage } from "./personadiaryDailyGuide";
import kernelDoc from "../../public/data/sasang_design_primitive_kernel_v1.json";
import emotionDoc from "../../public/data/sasang_emotion_mapping_v1.json";

export type SasangConstitution = "taeyang" | "soyang" | "taeeum" | "soeumin";
export type PathologyState = "calm" | "watch" | "stress" | "crisis";
export type HarmonyPairKind = "same" | "generating" | "controlling";

export type DesignKernelResolved = {
  schema: "personadiary_design_kernel_resolved_v1";
  kernel_version: string;
  product: "personadiary.com";
  pathology_state: PathologyState;
  stress_proxy: number;
  constitution_seed: SasangConstitution;
  intensity_budget: number;
  motion_cap: number;
  max_simultaneous_blocks: number;
  layout_density: number;
  contrast_cap: number;
  harmony_pair: HarmonyPairKind;
  valence: number;
  arousal: number;
  pulse_period_ms: number;
};

type KernelDoc = typeof kernelDoc;
type EmotionDoc = typeof emotionDoc;

const KERNEL = kernelDoc as KernelDoc;
const EMOTION = emotionDoc as EmotionDoc;
const PRODUCT = "personadiary.com";

const CONSTITUTION_ORDER: SasangConstitution[] = ["taeyang", "soyang", "taeeum", "soeumin"];

function hashDateKey(key: string): number {
  let h = 0;
  for (let i = 0; i < key.length; i++) {
    h = (h * 31 + key.charCodeAt(i)) >>> 0;
  }
  return h;
}

function pkgTextBlob(pkg: DailyGuidePackage): string {
  const parts: string[] = [];
  for (const sec of pkg.sections || []) {
    parts.push(...(sec.lines || []).map(String));
  }
  for (const block of pkg.ui_blocks || []) {
    if (block.body_ko) parts.push(block.body_ko);
  }
  return parts.join("\n");
}

/** Consumer-safe stress proxy — no clinical labels in UI. */
export function inferStressProxy(pkg: DailyGuidePackage | null, calendarKst: string): number {
  if (!pkg) {
    return 0.25 + (hashDateKey(calendarKst) % 100) / 500;
  }
  const blob = pkgTextBlob(pkg);
  if (/위기|긴급|panic|crisis/i.test(blob)) return 0.78;
  if (/잡음|과열|압박|긴장|스트레스|WATCH/i.test(blob)) return 0.62;
  if (/회복|수면|페이싱|쉬어|잔잔|관측 우선/i.test(blob)) return 0.4;
  return 0.28;
}

export function stressToPathologyState(stress: number): PathologyState {
  const s = KERNEL.primitives.pathology.states;
  const crisisGte = s.crisis.stress_gte ?? 0.75;
  const stressLt = s.stress.stress_lt ?? 0.75;
  const watchLt = s.watch.stress_lt ?? 0.55;
  const calmLt = s.calm.stress_lt ?? 0.35;
  if (stress >= crisisGte) return "crisis";
  if (stress >= watchLt && stress < stressLt) return "stress";
  if (stress >= calmLt && stress < watchLt) return "watch";
  return "calm";
}

/** Constitution seed — package hint or date hash (not clinical typing). */
export function inferConstitutionSeed(
  pkg: DailyGuidePackage | null,
  calendarKst: string
): SasangConstitution {
  const blob = pkg ? pkgTextBlob(pkg) : "";
  if (/소음인/.test(blob)) return "soeumin";
  if (/태음인/.test(blob)) return "taeeum";
  if (/소양인/.test(blob)) return "soyang";
  if (/태양인/.test(blob)) return "taeyang";
  const idx = hashDateKey(calendarKst || "today") % CONSTITUTION_ORDER.length;
  return CONSTITUTION_ORDER[idx];
}

function pairKey(a: string, b: string): string {
  return `${a}:${b}`;
}

function harmonyPairKind(
  primary: SasangConstitution,
  secondary: SasangConstitution
): HarmonyPairKind {
  if (primary === secondary) return "same";
  const harmony = KERNEL.primitives.harmony;
  const gen = (harmony.generating_pairs || []).some(
    ([x, y]) => pairKey(x, y) === pairKey(primary, secondary) || pairKey(y, x) === pairKey(primary, secondary)
  );
  if (gen) return "generating";
  const ctrl = (harmony.controlling_pairs || []).some(
    ([x, y]) => pairKey(x, y) === pairKey(primary, secondary) || pairKey(y, x) === pairKey(primary, secondary)
  );
  if (ctrl) return "controlling";
  return "same";
}

function secondaryConstitution(calendarKst: string): SasangConstitution {
  const idx = (hashDateKey(calendarKst) >>> 3) % CONSTITUTION_ORDER.length;
  return CONSTITUTION_ORDER[idx];
}

function pathologyParams(state: PathologyState) {
  const row = KERNEL.primitives.pathology.states[state];
  return {
    intensity_budget: row.intensity_budget,
    motion_cap: row.motion_cap,
    max_simultaneous_blocks: row.max_simultaneous_blocks,
  };
}

function pulsePeriodMs(motionCap: number): number {
  const [lo, hi] = KERNEL.primitives.circulation.default_range.pulse_period_ms;
  const t = 1 - motionCap;
  return Math.round(lo + (hi - lo) * t);
}

export function resolveDesignKernelForPersonadiary(
  pkg: DailyGuidePackage | null,
  calendarKst: string
): DesignKernelResolved {
  const depth = KERNEL.product_depth[PRODUCT];
  if (!depth) {
    throw new Error("personadiary.com missing from design kernel product_depth");
  }

  const stress = inferStressProxy(pkg, calendarKst);
  const pathology_state = stressToPathologyState(stress);
  const pathology = pathologyParams(pathology_state);

  const constitution_seed = inferConstitutionSeed(pkg, calendarKst);
  const harmony_pair = depth.primitives.includes("harmony")
    ? harmonyPairKind(constitution_seed, secondaryConstitution(calendarKst))
    : "same";
  const harmonyRule = KERNEL.primitives.harmony.pair_rules[harmony_pair];

  const anchors = EMOTION.anchors as Record<SasangConstitution, { valence: number; arousal: number }>;
  const va = anchors[constitution_seed] || anchors.taeyang;

  return {
    schema: "personadiary_design_kernel_resolved_v1",
    kernel_version: KERNEL.kernel_version,
    product: PRODUCT,
    pathology_state,
    stress_proxy: Math.round(stress * 1000) / 1000,
    constitution_seed,
    intensity_budget: pathology.intensity_budget,
    motion_cap: pathology.motion_cap,
    max_simultaneous_blocks: pathology.max_simultaneous_blocks,
    layout_density: harmonyRule.layout_density,
    contrast_cap: harmonyRule.contrast_cap,
    harmony_pair,
    valence: va.valence,
    arousal: va.arousal,
    pulse_period_ms: pulsePeriodMs(pathology.motion_cap),
  };
}

function parseHex(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const n = parseInt(h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function toHex(r: number, g: number, b: number): string {
  const R = Math.max(0, Math.min(255, Math.round(r)));
  const G = Math.max(0, Math.min(255, Math.round(g)));
  const B = Math.max(0, Math.min(255, Math.round(b)));
  return `#${R.toString(16).padStart(2, "0")}${G.toString(16).padStart(2, "0")}${B.toString(16).padStart(2, "0")}`;
}

/** VA + contrast_cap nudge on palette accents (base gradient from date hash). */
export function applyDesignKernelToPalette<T extends { accent: string; orb: string }>(
  palette: T,
  kernel: DesignKernelResolved
): T {
  const warmth = kernel.valence * 0.35 + kernel.arousal * 0.15;
  const [ar, ag, ab] = parseHex(palette.accent);
  const [or, og, ob] = parseHex(palette.orb);
  const delta = Math.round(warmth * 28);
  const damp = 0.85 + kernel.contrast_cap * 0.15;
  return {
    ...palette,
    accent: toHex(ar + delta, ag + delta * 0.4, ab - delta * 0.5),
    orb: toHex(or + delta * damp, og + delta * 0.3 * damp, ob - delta * 0.4 * damp),
  };
}

export function getDesignKernelMeta(): { kernel_version: string; charter_ref: string } {
  return {
    kernel_version: KERNEL.kernel_version,
    charter_ref: KERNEL.charter_ref,
  };
}
