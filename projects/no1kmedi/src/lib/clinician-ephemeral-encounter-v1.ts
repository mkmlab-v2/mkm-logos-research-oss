/**
 * One-off clinic encounters without Human Gold SSOT (Paste Chart P1).
 */

import type { PatientSsotPointer } from "@/lib/clinician-patient-slug-v1";

export function buildEphemeralEncounterSlug(displayLabel: string): string {
  const stem = displayLabel
    .trim()
    .replace(/\s+/g, "_")
    .replace(/[^a-zA-Z0-9가-힣_]/g, "")
    .slice(0, 24);
  const suffix = Date.now().toString(36).slice(-6);
  return `ephemeral_${stem || "patient"}_${suffix}`.toLowerCase();
}

export function buildEphemeralEncounterPointer(slug: string, displayLabel: string): PatientSsotPointer {
  return {
    schema: "ephemeral_encounter_pointer_v1",
    display_label: displayLabel.trim() || slug,
    ref_token: `EPH-${slug}`,
    paths: {},
  };
}

export function canUseEphemeralEncounter(args: {
  allowEphemeral?: boolean;
  display?: string;
  birthInstantUtc?: string;
}): boolean {
  if (!args.allowEphemeral) return false;
  return Boolean(args.display?.trim() && args.birthInstantUtc?.trim());
}
