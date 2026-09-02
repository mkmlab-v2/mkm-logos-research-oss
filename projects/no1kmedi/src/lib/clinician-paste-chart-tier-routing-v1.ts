/**
 * Paste Chart tier routing — manifest-driven LLM priority (Track B).
 */

import type { LlmPriority } from "@/lib/ai-provider";

import manifest from "@/lib/clinician-paste-chart-tier-manifest-v1.json";

export type PasteChartTierTaskId =
  | "paste_extract_regex"
  | "paste_extract_llm_low_confidence"
  | "paste_extract_llm_escalate"
  | "paste_chart_cds";

type TaskRow = {
  tier?: number;
  priority?: string;
  provider?: string;
  feature?: string;
  escalate_when?: string;
};

const TASKS = manifest.tasks as Record<PasteChartTierTaskId, TaskRow>;

const PRIORITY_SET = new Set<LlmPriority>([
  "auto",
  "azure_first",
  "azure_only",
  "gemini_first",
  "openrouter_first",
  "local_first",
  "gemini_only",
  "openrouter_only",
  "local_only",
]);

function parsePriority(raw?: string): LlmPriority {
  const p = (raw || "azure_first").trim().toLowerCase() as LlmPriority;
  return PRIORITY_SET.has(p) ? p : "azure_first";
}

export function resolvePasteChartTierPriority(taskId: PasteChartTierTaskId): LlmPriority {
  return parsePriority(TASKS[taskId]?.priority);
}

/** Tier-1 local_first on low-confidence extract; tier-2 azure_first after parse failure. */
export function resolvePasteExtractLlmPriority(opts: {
  baselineConfidence: "low" | "high";
  tier1Failed?: boolean;
}): { taskId: PasteChartTierTaskId; priority: LlmPriority } {
  if (opts.tier1Failed || opts.baselineConfidence === "high") {
    return {
      taskId: "paste_extract_llm_escalate",
      priority: resolvePasteChartTierPriority("paste_extract_llm_escalate"),
    };
  }
  return {
    taskId: "paste_extract_llm_low_confidence",
    priority: resolvePasteChartTierPriority("paste_extract_llm_low_confidence"),
  };
}

export function pasteChartTierManifestForDebug(): typeof manifest {
  return manifest;
}
