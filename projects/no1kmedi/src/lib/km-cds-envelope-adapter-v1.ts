/**
 * Maps jema-ai CDSS (`patient_consult_input_v1` + `consult_draft_v1`) to
 * monorepo SSOT payload for `km_physician_cds_assist_envelope_v1`
 * (`scripts/build_km_physician_cds_assist_envelope_v1.py`).
 *
 * Clinical boundaries unchanged: assist-only, physician final authority.
 */

import type { CdssCitationV1, ConsultDraftV1, PatientConsultInputV1 } from "./cdss-contract";

export type KmEvidenceAssessmentV1 = "sufficient" | "partial" | "insufficient";

export type KmPhysicianCdsPayloadV1 = {
  clinical_question: string;
  evidence_assessment: KmEvidenceAssessmentV1;
  evidence_gap_notes?: string;
  patient_context_summary?: string;
  evidence_items?: KmEvidenceItemV1[];
  differential_framework?: KmDifferentialFrameworkItemV1[];
  red_flags_and_escalation?: string[];
  suggested_next_steps_for_physician?: string[];
  confidence?: { overall_0_1: number; rationale: string };
  rag_manifest?: { corpus_id: string; snapshot_version?: string; chunk_ids?: string[] }[];
  audit?: {
    pipeline_run_id?: string;
    generator_model?: string;
    deterministic_input_sha256?: string;
  };
  disclaimer_ack?: string;
};

export type KmEvidenceItemV1 = {
  claim: string;
  evidence_grade:
    | "guideline"
    | "textbook"
    | "primary_lit"
    | "secondary_lit"
    | "internal_protocol"
    | "encyclopedic_ref"
    | "other";
  citation: {
    source_id: string;
    chunk_ref?: string;
    document_version?: string;
    retrieved_at_utc?: string;
    uri?: string;
  };
  relevance?: "high" | "medium" | "low";
  notes?: string;
};

export type KmDifferentialFrameworkItemV1 = {
  label: string;
  hypothesis_only: true;
  supporting_points?: string[];
  mitigating_or_contraindicating_points?: string[];
};

const DEFAULT_DISCLAIMER_ACK =
  "This CDS artifact assists licensed physicians only; not a standalone diagnosis or prescription.";

function literatureCitationCount(citations: CdssCitationV1[]): number {
  return citations.filter((c) => {
    const idBased = c.citation_id.startsWith("lit_");
    const refBased = c.source_ref.toLowerCase().startsWith("epmc:");
    return idBased || refBased;
  }).length;
}

function mapEvidenceLevel(level: CdssCitationV1["evidence_level"]): KmEvidenceItemV1["evidence_grade"] {
  if (level === "A") return "textbook";
  if (level === "B") return "secondary_lit";
  return "encyclopedic_ref";
}

function mapCitationToEvidenceItem(c: CdssCitationV1, relevance: KmEvidenceItemV1["relevance"]): KmEvidenceItemV1 {
  const sourceId = c.citation_id?.trim() || c.source_ref?.trim() || "unknown-source";
  return {
    claim: c.source_excerpt?.trim() || c.source_title?.trim() || "Citation excerpt unavailable.",
    evidence_grade: mapEvidenceLevel(c.evidence_level),
    citation: {
      source_id: sourceId,
      chunk_ref: c.source_ref?.startsWith("canon://") ? c.source_ref : undefined,
      uri: c.source_ref?.startsWith("http") ? c.source_ref : undefined,
    },
    relevance,
  };
}

function buildClinicalQuestion(input: PatientConsultInputV1): string {
  const cc = input.lane_b_clinical.chief_complaint.trim();
  const onset = input.lane_b_clinical.onset.trim();
  return (
    `Given chief complaint "${cc}" (onset: ${onset}), ` +
    "what bianzheng-oriented considerations and safety nets should the physician review before therapy changes?"
  );
}

function buildPatientContextSummary(input: PatientConsultInputV1, draft: ConsultDraftV1): string {
  const lines = [
    draft.clinical_summary.trim(),
    `Sasang candidate (assist): ${draft.profile_summary.sasang_candidate}`,
    `Manseryeok ref (${draft.profile_summary.saju_source}): ${draft.profile_summary.saju_reference}`,
    `Severity: ${input.lane_b_clinical.severity}`,
    `Medication: ${input.lane_b_clinical.medication || "not reported"}`,
  ];
  const triage = input.lane_b_clinical.patient_intake_context?.triage_level;
  if (triage) lines.push(`Triage hint: ${triage}`);
  return lines.join("\n").slice(0, 8000);
}

function assessEvidence(
  draft: ConsultDraftV1,
  literatureCount: number,
): { assessment: KmEvidenceAssessmentV1; gapNotes?: string } {
  const llmUsed = draft.generation?.llm_used === true;
  const citationCount = draft.citations.length;

  if (!llmUsed) {
    const reason = draft.generation?.reason || "unknown";
    return {
      assessment: "partial",
      gapNotes:
        `Neural CDSS reasoning was not used (reason=${reason}); draft uses deterministic template fallback. Physician should reconcile with bedside data and local protocols.`,
    };
  }
  if (citationCount === 0) {
    return {
      assessment: "insufficient",
      gapNotes:
        "No citations were attached to this CDS pass; verify institutional corpus indexing and repeat retrieval before clinical use.",
    };
  }
  if (literatureCount >= 1 && citationCount >= 2) {
    return { assessment: "sufficient" };
  }
  return {
    assessment: "partial",
    gapNotes:
      literatureCount === 0
        ? "Canon/static citations only; indexed literature passages were not retrieved for this query snapshot."
        : "Limited citation coverage; expand literature retrieval or local protocol check before relying on this pass.",
  };
}

function buildRedFlags(input: PatientConsultInputV1, draft: ConsultDraftV1): string[] {
  const items: string[] = [];
  const rf = input.lane_b_clinical.health_survey?.red_flag_notes?.trim();
  if (rf) items.push(rf);
  const caution = draft.reasoning.caution?.trim();
  if (caution) items.push(caution);
  if (input.lane_b_clinical.patient_intake_context?.triage_level === "emergency") {
    items.push("Intake triage marked emergency — prioritize in-person evaluation per hospital policy.");
  }
  return items.length ? items : ["Review standard acute red-flag sets per institutional policy."];
}

function buildSuggestedSteps(draft: ConsultDraftV1): string[] {
  const care = draft.reasoning.care_direction?.trim();
  if (!care) return ["Expand history and examination before finalizing bianzheng and treatment plan."];
  const parts = care
    .split(/[.;]\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 8);
  return parts.length ? parts.slice(0, 6) : [care];
}

export type BuildKmCdsPayloadOptions = {
  /** ISO-8601 timestamp for citation audit fields */
  retrievedAtUtc?: string;
};

/**
 * Build SSOT-compatible CDS envelope payload (pre-Python validation).
 */
export function buildKmPhysicianCdsPayloadFromConsult(
  input: PatientConsultInputV1,
  draft: ConsultDraftV1,
  options: BuildKmCdsPayloadOptions = {},
): KmPhysicianCdsPayloadV1 {
  const retrievedAt = options.retrievedAtUtc || new Date().toISOString();
  const litCount = literatureCitationCount(draft.citations);
  const { assessment, gapNotes } = assessEvidence(draft, litCount);

  const evidenceItems = draft.citations.map((c, idx) =>
    mapCitationToEvidenceItem(c, idx === 0 ? "high" : litCount > 0 && c.citation_id.startsWith("lit_") ? "high" : "medium"),
  );

  const confidenceScore = assessment === "sufficient" ? 0.72 : assessment === "partial" ? 0.55 : 0.38;
  const confidenceRationale =
    assessment === "sufficient"
      ? "LLM reasoning with canon and literature citations attached; physician must still confirm at bedside."
      : assessment === "partial"
        ? gapNotes || "Partial evidence coverage."
        : gapNotes || "Insufficient indexed evidence for this pass.";

  const payload: KmPhysicianCdsPayloadV1 = {
    clinical_question: buildClinicalQuestion(input),
    evidence_assessment: assessment,
    patient_context_summary: buildPatientContextSummary(input, draft),
    evidence_items: evidenceItems,
    differential_framework: [
      {
        label: draft.reasoning.syndrome_hypothesis.trim().slice(0, 500) || "Syndrome hypothesis pending physician review",
        hypothesis_only: true,
        supporting_points: [draft.clinical_summary.trim()].filter(Boolean),
        mitigating_or_contraindicating_points: buildRedFlags(input, draft).slice(0, 4),
      },
    ],
    red_flags_and_escalation: buildRedFlags(input, draft),
    suggested_next_steps_for_physician: buildSuggestedSteps(draft),
    confidence: { overall_0_1: confidenceScore, rationale: confidenceRationale },
    rag_manifest: [
      {
        corpus_id: "jema-ai-cdss-runtime",
        snapshot_version: "consult_draft_v1",
        chunk_ids: draft.citations.map((c) => c.citation_id).filter(Boolean),
      },
    ],
    audit: {
      pipeline_run_id: input.request_id,
      generator_model: draft.generation?.llm_used ? "jema-ai-cdss-llm" : `jema-ai-cdss-fallback:${draft.generation?.reason || "template"}`,
    },
    disclaimer_ack: DEFAULT_DISCLAIMER_ACK,
  };

  if (gapNotes && (assessment === "partial" || assessment === "insufficient")) {
    payload.evidence_gap_notes = gapNotes;
  }

  for (const item of payload.evidence_items || []) {
    if (!item.citation.retrieved_at_utc) {
      item.citation.retrieved_at_utc = retrievedAt;
    }
  }

  return payload;
}
