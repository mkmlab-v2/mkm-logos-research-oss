/**
 * Logos Studio query pipeline chips (client · research_only).
 */

import type { OmniPipelineChipV1 } from "@/components/OmniPipelineStatusChips";

export const LOGOS_QUERY_PIPELINE_STAGE_IDS = [
  "query_nonempty",
  "path_engine",
  "citation_lock",
  "result_ready",
] as const;

export type LogosQueryPipelineStageId = (typeof LOGOS_QUERY_PIPELINE_STAGE_IDS)[number];

const LABELS: Record<LogosQueryPipelineStageId, string> = {
  query_nonempty: "질문 입력",
  path_engine: "경로 엔진",
  citation_lock: "인용 잠금",
  result_ready: "결과",
};

export function createLogosQueryPipeline(): OmniPipelineChipV1[] {
  return LOGOS_QUERY_PIPELINE_STAGE_IDS.map((id) => ({
    id,
    label_ko: LABELS[id],
    status: "pending",
  }));
}

export function patchLogosQueryPipeline(
  pipeline: OmniPipelineChipV1[],
  id: LogosQueryPipelineStageId,
  status: OmniPipelineChipV1["status"],
): OmniPipelineChipV1[] {
  return pipeline.map((stage) => (stage.id === id ? { ...stage, status } : stage));
}

export function resetLogosQueryPipeline(): OmniPipelineChipV1[] {
  return createLogosQueryPipeline();
}
