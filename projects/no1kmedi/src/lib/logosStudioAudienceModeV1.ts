/** Logos Studio audience mode — same shell, tone/disclaimer branch only. research_only · HOLD */
export type LogosStudioAudienceMode = "academic" | "pastoral";

export const LOGOS_STUDIO_AUDIENCE_MODES: LogosStudioAudienceMode[] = ["academic", "pastoral"];

/** Curated presets for 묵상·고민 mode (not pastoral counseling product). */
export const LOGOS_PASTORAL_PRESET_IDS: readonly string[] = [
  "job_job_suffering_reason",
  "job_existential_suffering",
  "topic_ps_23_anchor",
  "topic_ps_103_anchor",
  "topic_ps_89_anchor",
  "topic_job_38_anchor",
  "topic_job_42_anchor",
] as const;

const PASTORAL_PRESET_SET = new Set<string>(LOGOS_PASTORAL_PRESET_IDS);

export const LOGOS_PASTORAL_SLOT_LABEL_KO = "묵상·고민";

export function parseLogosStudioAudienceMode(raw: string | null | undefined): LogosStudioAudienceMode {
  const v = (raw || "").trim().toLowerCase();
  return v === "pastoral" ? "pastoral" : "academic";
}

export function isPastoralPresetId(presetId: string | null | undefined): boolean {
  return !!presetId && PASTORAL_PRESET_SET.has(presetId);
}

export function filterPresetsByAudienceMode<T extends { id: string }>(
  presets: T[],
  mode: LogosStudioAudienceMode,
): T[] {
  if (mode === "academic") return presets;
  return presets.filter((p) => PASTORAL_PRESET_SET.has(p.id));
}

export function defaultPresetIdForAudienceMode(mode: LogosStudioAudienceMode): string {
  return mode === "pastoral" ? "job_job_suffering_reason" : "job_job_suffering_reason";
}
