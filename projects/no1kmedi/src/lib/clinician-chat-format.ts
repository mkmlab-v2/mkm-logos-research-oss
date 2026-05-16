import type { ClinicianCdsSnapshot } from "@/lib/clinician-chat-types";

type CdsDraftLike = {
  clinical_summary: string;
  profile_summary?: { sasang_candidate?: string; saju_reference?: string };
  reasoning: { syndrome_hypothesis: string; care_direction: string; caution: string };
  non_medical_notice?: string;
};

export function formatCdsAssistantMessage(
  draft: CdsDraftLike,
  kmCds?: { validation?: { ok: boolean; method?: string; error?: string } },
): string {
  const lines: string[] = [];
  lines.push(draft.clinical_summary.trim());
  lines.push("");
  if (draft.profile_summary?.sasang_candidate) {
    lines.push(`체질 후보: ${draft.profile_summary.sasang_candidate}`);
  }
  if (draft.profile_summary?.saju_reference) {
    lines.push(`만세력 참고: ${draft.profile_summary.saju_reference}`);
  }
  lines.push("");
  lines.push(`변증 가설: ${draft.reasoning.syndrome_hypothesis}`);
  lines.push(`케어 방향: ${draft.reasoning.care_direction}`);
  lines.push(`주의: ${draft.reasoning.caution}`);
  if (kmCds?.validation) {
    lines.push("");
    lines.push(
      kmCds.validation.ok
        ? "SSOT 봉투 검증: 통과 (Python)"
        : `SSOT 봉투: ${kmCds.validation.method || "미검증"}${kmCds.validation.error ? ` — ${kmCds.validation.error}` : ""}`,
    );
  }
  if (draft.non_medical_notice) {
    lines.push("");
    lines.push(draft.non_medical_notice);
  }
  return lines.join("\n");
}

export function cdsSnapshotFromApi(
  requestId: string,
  draft: CdsDraftLike,
  kmCds?: {
    envelope?: Record<string, unknown>;
    validation?: { ok: boolean };
  },
): ClinicianCdsSnapshot {
  return {
    requestId,
    clinicalSummary: draft.clinical_summary,
    reasoning: draft.reasoning,
    envelope: kmCds?.envelope,
    validationOk: kmCds?.validation?.ok === true,
  };
}
