export type DailyGuideBlock = {
  type: string;
  title_ko: string;
  body_ko?: string;
  ref?: string;
  badge_ko?: string;
  mkmlife_href?: string;
  evidence_tier?: "literature_supported" | "coaching_heuristic" | "delight" | string;
};

export type MomentPresetPolishEntry = {
  canonical_query?: string;
  summary_ko_deterministic?: string;
  summary_ko_polished?: string | null;
  polish_meta?: Record<string, unknown>;
};

export type MomentPresetPolishBlock = {
  schema?: string;
  hypothesis_tier?: string;
  lane?: string;
  presets?: Partial<Record<string, MomentPresetPolishEntry>>;
  hero?: {
    body_ko_deterministic?: string;
    body_ko_polished?: string | null;
    polish_meta?: Record<string, unknown>;
  };
};

export type DailyGuidePackage = {
  schema?: string;
  profile_id?: string;
  city_default?: string;
  calendar_kst?: string;
  concept_ko?: string;
  sections?: { id?: string; title_ko?: string; lines?: string[] }[];
  ui_blocks?: DailyGuideBlock[];
  reflect_template_ko?: string;
  disclaimer_ko?: string;
  moment_preset_polish_v1?: MomentPresetPolishBlock;
  source_iws_v2?: boolean;
  iws_v2_overlay_applied?: boolean;
};

export const IWS_OVERLAY_STATIC_PATHS = [
  "/data/integrated_wellness/personadiary_iws_overlay_v1.json",
  "/data/integrated_wellness/personadiary_daily_package_latest.json",
] as const;

function isIwsMyeongniCard(block: DailyGuideBlock): boolean {
  return (block.title_ko || "").includes("명리 참고");
}

function isIwsBodyRhythmCard(block: DailyGuideBlock): boolean {
  const title = block.title_ko || "";
  return block.type === "card" && title.startsWith("몸·리듬 —") && !isIwsMyeongniCard(block);
}

/** Merge B-track IWS wellness cards into profile daily package (commander keeps full 명리). */
export function mergeIwsWellnessOverlay(
  base: DailyGuidePackage,
  overlay: DailyGuidePackage | null,
): DailyGuidePackage {
  if (!overlay?.source_iws_v2 || !overlay.ui_blocks?.length) {
    return base;
  }

  const blocks = [...(base.ui_blocks || [])];
  const overlayBlocks = overlay.ui_blocks;

  const iwsMyeongni = overlayBlocks.find(isIwsMyeongniCard);
  if (iwsMyeongni && !blocks.some(isIwsMyeongniCard)) {
    const heroIdx = blocks.findIndex((b) => b.type === "hero");
    blocks.splice(heroIdx >= 0 ? heroIdx + 1 : 0, 0, iwsMyeongni);
  }

  for (const ob of overlayBlocks) {
    if (!isIwsBodyRhythmCard(ob)) continue;
    if (blocks.some((b) => b.title_ko === ob.title_ko)) continue;
    blocks.push(ob);
  }

  return {
    ...base,
    ui_blocks: blocks,
    iws_v2_overlay_applied: true,
  };
}

export function isPersonadiaryDailyPackage(doc: unknown): doc is DailyGuidePackage {
  return (
    typeof doc === "object" &&
    doc !== null &&
    (doc as DailyGuidePackage).schema === "personadiary_daily_response_package_v1"
  );
}
