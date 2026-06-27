/** Logos commercial workspace routes (logos.jema-ai.com · same paths on jema hub host). */

export const LOGOS_RESEARCH_HOME = "/logos-research";
export const LOGOS_RESEARCH_STUDIO = "/logos-research/studio";

export const LOGOS_QUESTION_HINTS = [
  "성경",
  "logos",
  "graphrag",
  "graph studio",
  "구절",
  "topology",
  "citation",
  "렘마",
  "crosswalk",
  "토폴로지",
] as const;

export function questionMatchesLogosCommercial(question: string): boolean {
  const lower = question.toLowerCase();
  return LOGOS_QUESTION_HINTS.some(
    (h) => lower.includes(h.toLowerCase()) || question.includes(h),
  );
}

export function buildLogosStudioHubRoute(prefill?: string): string {
  const q = prefill?.trim();
  if (!q) return `${LOGOS_RESEARCH_STUDIO}?source=jema_hub_v2`;
  return `${LOGOS_RESEARCH_STUDIO}?q=${encodeURIComponent(q)}&source=jema_hub_v2`;
}
