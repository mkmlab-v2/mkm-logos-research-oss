/** Myeongni commercial workspace routes (jema-ai.com hub · B-track research_only). */

export const MYEONGNI_RESEARCH_STUDIO = "/myeongni-research/studio";

export const MYEONGNI_QUESTION_HINTS = [
  "명리",
  "사주",
  "대운",
  "세운",
  "십성",
  "오행",
  "용신",
  "四柱",
] as const;

export function questionMatchesMyeongniCommercial(question: string): boolean {
  const lower = question.toLowerCase();
  return MYEONGNI_QUESTION_HINTS.some(
    (h) => lower.includes(h.toLowerCase()) || question.includes(h),
  );
}

export function buildMyeongniStudioHubRoute(prefill?: string): string {
  const q = prefill?.trim();
  if (!q) return `${MYEONGNI_RESEARCH_STUDIO}?source=jema_hub_v2`;
  return `${MYEONGNI_RESEARCH_STUDIO}?q=${encodeURIComponent(q)}&source=jema_hub_v2`;
}
