/**
 * Gate1 Arm A xref shrink — commander-adopted engine policy (2026-08-10).
 *
 * Soft-drop known soft-parallel / xref satellites + cap max_refs=6.
 * research_only · SEND HOLD · product_all_ok=false · harness≠product · ≠Destiny
 *
 * SSOT freeze: docs/final/artifacts/logos_ask_anchor_fitness_gate1_arm_a_frozen_v1_latest.json
 */
export const ARM_A_ENGINE_ADOPT_STATUS = "ADOPTED" as const;

export const ARM_A_XREF_SOFT_DROP = [
  "Acts.16.18",
  "Heb.10.19",
  "Heb.10.20",
  "John.14.6",
] as const;

export const ARM_A_XREF_MAX_REFS = 6;

const SOFT_DROP_SET = new Set(
  ARM_A_XREF_SOFT_DROP.map((r) => r.replace(/\s+/g, "").toLowerCase()),
);

function normRef(ref: string): string {
  return String(ref || "").trim().replace(/\s+/g, "");
}

/** Post-filter verse_refs — Arm A soft-drop + max_refs (order-preserving). */
export function applyArmAXrefShrinkV1(verseRefs: readonly string[]): string[] {
  const out: string[] = [];
  for (const raw of verseRefs || []) {
    const t = normRef(raw);
    if (!t) continue;
    if (SOFT_DROP_SET.has(t.toLowerCase())) continue;
    out.push(t);
    if (out.length >= ARM_A_XREF_MAX_REFS) break;
  }
  return out;
}
