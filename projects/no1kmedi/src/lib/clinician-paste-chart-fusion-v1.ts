import type { PasteChartFusionContextV1 } from "@/lib/clinician-chat-types";

export type PasteChartSessionSyncV1 = {
  patientLabel: string;
  title: string;
  chartSnippet: string;
  summarySnippet: string;
  birthInstantUtc?: string;
  ianaTz?: string;
  chiefComplaint?: string;
  slug?: string;
  adviceTitles?: string[];
  assessmentLine?: string;
  ephemeral?: boolean;
};

export function buildPasteChartFusionAssistantMessage(
  session: Pick<PasteChartSessionSyncV1, "summarySnippet" | "adviceTitles">,
): string {
  const adviceLine =
    session.adviceTitles?.length && session.adviceTitles.length > 0
      ? `조언 카드: ${session.adviceTitles.slice(0, 6).join(" · ")}`
      : "";
  return [session.summarySnippet, adviceLine].filter(Boolean).join("\n\n") || "Paste Chart 분석 완료";
}

export function buildPasteChartFusionContext(
  session: PasteChartSessionSyncV1,
): PasteChartFusionContextV1 {
  return {
    syncedAt: Date.now(),
    patientLabel: session.patientLabel,
    adviceTitles: session.adviceTitles || [],
    assessmentLine: session.assessmentLine,
    ephemeral: session.ephemeral,
  };
}
