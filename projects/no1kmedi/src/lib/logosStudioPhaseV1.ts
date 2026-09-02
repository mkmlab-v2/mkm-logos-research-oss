/** Logos Studio omni entry → Scriptorium workspace phase (structure SSOT). */

export type LogosStudioPhase = "omni" | "workspace";

/** Quick-start chips on omni idle (allowlisted demo + smoke presets). */
export const LOGOS_STUDIO_OMNI_QUICK_PRESET_IDS = [
  "job_job_suffering_reason",
  "isaiah_youtube_spine_v1",
  "bigset_topic_nephilim",
] as const;

export type LogosStudioPhaseInit = {
  canvasLayout: boolean;
  embedHero: boolean;
  autorun: boolean;
  legacyLayout: boolean;
};

/** Deep links with autorun skip omni; bare /studio opens omni first. */
export function resolveInitialStudioPhase(opts: LogosStudioPhaseInit): LogosStudioPhase {
  if (!opts.canvasLayout || opts.embedHero || opts.legacyLayout || opts.autorun) {
    return "workspace";
  }
  return "omni";
}

export function shouldSkipOmniEntry(opts: LogosStudioPhaseInit): boolean {
  return resolveInitialStudioPhase(opts) === "workspace";
}
