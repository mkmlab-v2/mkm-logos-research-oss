/**
 * Paste Chart encounter session envelope + verification pipeline (Track B · client).
 * Single write owner: ClinicianEncounterGoldPanel.
 */

import type { PasteExtractDraftV1 } from "@/lib/clinician-chart-paste-extract-v1";

export const ENCOUNTER_PIPELINE_STAGE_IDS = [
  "chart_nonempty",
  "extract_draft_ok",
  "cds_request_sent",
  "cds_response_valid",
  "advice_gate_passed",
  "fusion_synced",
] as const;

export type EncounterPipelineStageId = (typeof ENCOUNTER_PIPELINE_STAGE_IDS)[number];

export type EncounterPipelineStageStatus =
  | "pending"
  | "active"
  | "ok"
  | "warn"
  | "fail"
  | "skipped";

export type EncounterPipelineStageV1 = {
  id: EncounterPipelineStageId;
  label_ko: string;
  status: EncounterPipelineStageStatus;
  error_code?: string;
  at_ms?: number;
};

export type EncounterSessionEnvelopeV1 = {
  schema: "encounter_session_envelope_v1";
  input: {
    chartText: string;
    objectiveDraft: string;
  };
  extract: PasteExtractDraftV1;
  patient: {
    lookup: string;
    slug?: string;
    displayLabel?: string;
  };
  pipeline: EncounterPipelineStageV1[];
  output: {
    fusionSynced: boolean;
    requestId?: string;
    hasAdvice: boolean;
    adviceWarning?: string | null;
  };
};

export const ENCOUNTER_PIPELINE_STAGE_LABELS: Record<EncounterPipelineStageId, string> = {
  chart_nonempty: "차트 입력",
  extract_draft_ok: "칩 추출",
  cds_request_sent: "CDSS 요청",
  cds_response_valid: "SOAP 생성",
  advice_gate_passed: "조언 검증",
  fusion_synced: "대화 연동",
};

export function createInitialEncounterPipeline(): EncounterPipelineStageV1[] {
  return ENCOUNTER_PIPELINE_STAGE_IDS.map((id) => ({
    id,
    label_ko: ENCOUNTER_PIPELINE_STAGE_LABELS[id],
    status: "pending",
  }));
}

export function createInitialEncounterSessionEnvelope(
  partial?: Partial<Pick<EncounterSessionEnvelopeV1, "input" | "extract" | "patient">>,
): EncounterSessionEnvelopeV1 {
  return {
    schema: "encounter_session_envelope_v1",
    input: partial?.input ?? { chartText: "", objectiveDraft: "" },
    extract:
      partial?.extract ??
      ({
        schema: "paste_extract_draft_v1",
        confidence: "low",
        sources: [],
      } satisfies PasteExtractDraftV1),
    patient: partial?.patient ?? { lookup: "" },
    pipeline: createInitialEncounterPipeline(),
    output: { fusionSynced: false, hasAdvice: false },
  };
}

export function patchPipelineStage(
  pipeline: EncounterPipelineStageV1[],
  id: EncounterPipelineStageId,
  patch: Partial<Pick<EncounterPipelineStageV1, "status" | "error_code">>,
): EncounterPipelineStageV1[] {
  const now = Date.now();
  return pipeline.map((stage) => {
    if (stage.id !== id) return stage;
    const nextStatus = patch.status ?? stage.status;
    return {
      ...stage,
      ...patch,
      at_ms: nextStatus !== "pending" && nextStatus !== stage.status ? now : stage.at_ms,
    };
  });
}

export function resetEncounterPipeline(pipeline: EncounterPipelineStageV1[]): EncounterPipelineStageV1[] {
  return pipeline.map((stage) => ({
    ...stage,
    status: "pending",
    error_code: undefined,
    at_ms: undefined,
  }));
}

export function validateChartNonempty(chartText: string): { ok: boolean; error_code?: string } {
  if (!chartText.trim()) return { ok: false, error_code: "chart_text_required" };
  return { ok: true };
}

export function validateExtractDraftOk(args: {
  clinicianEmail?: string;
  hasPatientLookup: boolean;
  hasBirthOrSlug: boolean;
}): { ok: boolean; error_code?: string } {
  if (!args.clinicianEmail?.trim()) return { ok: false, error_code: "clinician_email_required" };
  if (!args.hasPatientLookup) return { ok: false, error_code: "patient_lookup_required" };
  if (!args.hasBirthOrSlug) return { ok: false, error_code: "birth_or_slug_required" };
  return { ok: true };
}

export function validateCdsBundle(bundle: unknown): {
  ok: boolean;
  error_code?: string;
  requestId?: string;
} {
  if (!bundle || typeof bundle !== "object") return { ok: false, error_code: "cds_bundle_missing" };
  const record = bundle as Record<string, unknown>;
  if (!record.clinical_soap_v1) return { ok: false, error_code: "clinical_soap_missing" };
  const requestId = typeof record.request_id === "string" ? record.request_id : undefined;
  return { ok: true, requestId };
}

export function resolveAdviceGateStatus(
  adviceError?: string | null,
  hasAdvice?: boolean,
): EncounterPipelineStageStatus {
  if (adviceError && !hasAdvice) return "fail";
  if (adviceError && hasAdvice) return "warn";
  return hasAdvice ? "ok" : "skipped";
}

export type EncounterEnvelopeAction =
  | { type: "set_chart_text"; value: string }
  | { type: "set_objective"; value: string }
  | { type: "set_extract"; draft: PasteExtractDraftV1 }
  | { type: "set_lookup"; value: string }
  | { type: "set_patient_meta"; slug?: string; displayLabel?: string }
  | { type: "reset_pipeline" }
  | { type: "begin_analyze" }
  | {
      type: "set_pipeline_stage";
      id: EncounterPipelineStageId;
      status: EncounterPipelineStageStatus;
      error_code?: string;
    }
  | { type: "set_output"; patch: Partial<EncounterSessionEnvelopeV1["output"]> }
  | { type: "clear_output" };

export function encounterSessionEnvelopeReducer(
  state: EncounterSessionEnvelopeV1,
  action: EncounterEnvelopeAction,
): EncounterSessionEnvelopeV1 {
  switch (action.type) {
    case "set_chart_text":
      return { ...state, input: { ...state.input, chartText: action.value } };
    case "set_objective":
      return { ...state, input: { ...state.input, objectiveDraft: action.value } };
    case "set_extract":
      return { ...state, extract: action.draft };
    case "set_lookup":
      return { ...state, patient: { ...state.patient, lookup: action.value } };
    case "set_patient_meta":
      return {
        ...state,
        patient: {
          ...state.patient,
          slug: action.slug ?? state.patient.slug,
          displayLabel: action.displayLabel ?? state.patient.displayLabel,
        },
      };
    case "reset_pipeline":
      return { ...state, pipeline: resetEncounterPipeline(state.pipeline) };
    case "begin_analyze":
      return {
        ...state,
        pipeline: resetEncounterPipeline(state.pipeline),
        output: { fusionSynced: false, hasAdvice: false, adviceWarning: null },
      };
    case "set_pipeline_stage":
      return {
        ...state,
        pipeline: patchPipelineStage(state.pipeline, action.id, {
          status: action.status,
          error_code: action.error_code,
        }),
      };
    case "set_output":
      return { ...state, output: { ...state.output, ...action.patch } };
    case "clear_output":
      return {
        ...state,
        output: { fusionSynced: false, hasAdvice: false, adviceWarning: null },
      };
    default:
      return state;
  }
}

export function encounterPipelineToOmniChips(
  pipeline: EncounterPipelineStageV1[],
): Array<{ id: string; label_ko: string; status: EncounterPipelineStageStatus }> {
  return pipeline.map((stage) => ({
    id: stage.id,
    label_ko: stage.label_ko,
    status: stage.status,
  }));
}

/** Snapshot for ledger append when React reducer state may lag behind in-flight dispatches. */
export function buildEncounterEnvelopeForLedger(
  base: EncounterSessionEnvelopeV1,
  patch: {
    input?: Partial<EncounterSessionEnvelopeV1["input"]>;
    patient?: Partial<EncounterSessionEnvelopeV1["patient"]>;
    pipeline?: Array<{
      id: EncounterPipelineStageId;
      status: EncounterPipelineStageStatus;
      error_code?: string;
    }>;
    output?: Partial<EncounterSessionEnvelopeV1["output"]>;
  },
): EncounterSessionEnvelopeV1 {
  let pipeline = base.pipeline;
  if (patch.pipeline?.length) {
    for (const stagePatch of patch.pipeline) {
      pipeline = patchPipelineStage(pipeline, stagePatch.id, {
        status: stagePatch.status,
        error_code: stagePatch.error_code,
      });
    }
  }
  return {
    ...base,
    input: { ...base.input, ...patch.input },
    patient: { ...base.patient, ...patch.patient },
    pipeline,
    output: { ...base.output, ...patch.output },
  };
}
