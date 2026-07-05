/** Build canon cite lookup query from clinician thread / CDS snapshot (no PHI expansion). */

export function buildKmCanonCiteSuggestedQuery(input: {
  chiefComplaint?: string;
  syndromeHypothesis?: string;
  clinicalSummary?: string;
}): string {
  const cc = input.chiefComplaint?.trim() ?? "";
  const syndrome = input.syndromeHypothesis?.trim() ?? "";
  if (cc && syndrome) return `${cc} ${syndrome}`.slice(0, 120);
  if (cc) return cc.slice(0, 120);
  if (syndrome) return syndrome.slice(0, 120);
  const summary = input.clinicalSummary?.trim() ?? "";
  return summary.slice(0, 80);
}
