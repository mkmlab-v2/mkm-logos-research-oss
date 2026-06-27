/**
 * PersonaDiary persona visual card v1 — CSS snapshot card (no image gen).
 */
import type { DailyGuidePackage } from "./personadiaryDailyGuide";
import {
  applyDesignKernelToPalette,
  resolveDesignKernelForPersonadiary,
  type DesignKernelResolved,
} from "./personadiaryDesignKernelV1";
import { buildMomentNationView } from "./personadiaryMomentNationV1";
import {
  resolveMomentBundle,
  type MomentBundleResolved,
} from "./personadiaryMomentBundleV1";

export type PersonaVisualPalette = {
  id: string;
  gradient_from: string;
  gradient_to: string;
  accent: string;
  orb: string;
};

const PALETTES: PersonaVisualPalette[] = [
  { id: "dawn", gradient_from: "#4a2d6e", gradient_to: "#c45c3a", accent: "#ffd9a8", orb: "#ffb86b" },
  { id: "mist", gradient_from: "#2a3f5f", gradient_to: "#5a7a9a", accent: "#b8d4f0", orb: "#8ec5ff" },
  { id: "bloom", gradient_from: "#5c2d4a", gradient_to: "#9a4a6e", accent: "#ffc8e0", orb: "#ff9ec8" },
  { id: "grove", gradient_from: "#1f4a3a", gradient_to: "#3d7a5c", accent: "#b8f0d0", orb: "#7ee8b0" },
];

export type PersonaVisualCardView = {
  schema: "personadiary_persona_visual_card_v1";
  calendar_kst: string;
  city_label: string;
  title_ko: string;
  subtitle_ko: string;
  fusion_line: string;
  me_line: string;
  world_weather: string;
  delight_chip: string;
  keyword_ko: string;
  acode_public: string;
  acode_title: string;
  palette: PersonaVisualPalette;
  design_kernel: DesignKernelResolved;
  moment_bundle: MomentBundleResolved;
  watermark_ko: string;
  share_text_ko: string;
};

function hashDateKey(key: string): number {
  let h = 0;
  for (let i = 0; i < key.length; i++) {
    h = (h * 31 + key.charCodeAt(i)) >>> 0;
  }
  return h;
}

function pickPalette(calendarKst: string): PersonaVisualPalette {
  const idx = hashDateKey(calendarKst || "today") % PALETTES.length;
  return PALETTES[idx];
}

function keywordFromFusion(fusion: string): string {
  const t = fusion.replace(/[.…]/g, "").trim();
  if (t.length <= 12) return t || "한 박자 쉼";
  const tail = t.split(/\s+/).slice(-3).join(" ");
  return tail.slice(0, 16) || "찰나";
}

export function buildPersonaVisualCardView(
  pkg: DailyGuidePackage | null
): PersonaVisualCardView | null {
  const nation = buildMomentNationView(pkg);
  if (!nation) return null;

  const calendar = nation.calendar_kst || "—";
  const design_kernel = resolveDesignKernelForPersonadiary(pkg, calendar);
  const moment_bundle = resolveMomentBundle(pkg, "reflect", calendar);
  const palette = applyDesignKernelToPalette(pickPalette(calendar), design_kernel);
  const fusion = nation.fusion_line_cute;
  const me = nation.me_line_cute;
  const delight =
    nation.delight_meal || nation.delight_outfit || "오늘의 작은 기쁨";

  const shareText = [
    `🪞 Persona Diary · 찰나의 나 (${calendar})`,
    `${nation.acode_public} · ${nation.acode_title}`,
    fusion,
    `지금의 나: ${me}`,
    delight,
    "",
    "personadiary.com · preview_only · [가설]",
  ].join("\n");

  return {
    schema: "personadiary_persona_visual_card_v1",
    calendar_kst: calendar,
    city_label: nation.city_label,
    title_ko: "오늘의 나",
    subtitle_ko: "찰나의 나라 · 페르소나 카드",
    fusion_line: fusion,
    me_line: me,
    world_weather: nation.world_weather,
    delight_chip: delight,
    keyword_ko: keywordFromFusion(fusion),
    acode_public: nation.acode_public,
    acode_title: nation.acode_title,
    palette,
    design_kernel,
    moment_bundle,
    watermark_ko: "personadiary.com · preview_only · [가설]",
    share_text_ko: shareText,
  };
}
