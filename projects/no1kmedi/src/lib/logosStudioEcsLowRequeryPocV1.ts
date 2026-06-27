/** B-track PoC — ECS-low path expansion hint (research_only · NON_GATING · send_gate HOLD). */

export type EcsBand = "low" | "mid" | "high";

export function shouldSuggestEcsRequeryPoc(band: EcsBand | undefined): boolean {
  return band === "low";
}

export const ECS_LOW_REQUERY_POC_HINT_KO =
  "ECS low — 경로 깊이 확장 재조회 PoC (연구용 · 실행 신호 아님)";

/** Hover/focus tooltip — B2B demo + Studio header (research_only · NON_GATING). */
export const ECS_V1_TOOLTIP_KO =
  "ECS v1 (Evidence Confidence Score): 경로 깊이 40% + 인용 구절 40% − 학파 충돌 페널티 20%로 계산한 구조 신뢰도(0–100). [NON_GATING] 연구·감사 보조 지표이며 매매·Track A·실행 트리거가 아닙니다.";

export function ecsV1Tooltip(noteKo?: string | null): string {
  if (noteKo?.trim()) return `${ECS_V1_TOOLTIP_KO} ${noteKo.trim()}`;
  return ECS_V1_TOOLTIP_KO;
}

export function buildEcsExpandPocStudioUrl(presetId: string): string {
  const params = new URLSearchParams({
    q: presetId,
    autorun: "1",
    demo: "1",
    ecs_expand_poc: "1",
  });
  return `/logos-research/studio?${params.toString()}`;
}
