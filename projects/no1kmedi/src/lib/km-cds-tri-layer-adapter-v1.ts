/**
 * Build `mkm_bianzheng_tri_layer_v1` from jema-ai CDSS outputs (assist-only).
 */

import { createHash } from "node:crypto";

import type { CdssCitationV1, ConsultDraftV1, PatientConsultInputV1 } from "./cdss-contract";
import type { KmEvidenceAssessmentV1 } from "./km-cds-envelope-adapter-v1";

export type MkmBianzhengTriLayerV1 = {
  schema: "mkm_bianzheng_tri_layer_v1";
  version: "1.0.0";
  layer_a_engine: {
    engine_id: string;
    engine_version: string;
    input_schema_id: string;
    input_schema_version: string;
    ruleset_id: string;
    ruleset_version: string;
    run_id: string;
    generated_at_utc: string;
    deterministic_input_sha256: string;
    candidate_list: {
      candidate_id: string;
      kind: "constitution_pattern" | "syndrome_pattern" | "formula_hypothesis" | "other";
      label: string;
      score_0_1: number;
      rank: number;
      hypothesis_scope: "engine_hypothesis_only";
    }[];
  };
  layer_b_augmentation: {
    western_med_fallback: {
      binding: "reference_only_non_diagnostic";
      risk_gate: "GO" | "WATCH" | "HOLD";
      gate_rationale_ref: string;
      differential_hypotheses: {
        hypothesis_id: string;
        label: string;
        hypothesis_only: true;
        urgency: "routine" | "urgent" | "emergency_evaluate_local_protocol";
      }[];
      contraindication_flags: string[];
      escalation_prompts: string[];
    };
    literature_evidence: {
      evidence_id: string;
      corpus_id: string;
      corpus_snapshot_version: string;
      chunk_id: string;
      snippet_hash_sha256: string;
      evidence_grade: "guideline" | "primary_lit" | "secondary_lit" | "other";
      claim_scope: "supporting" | "contrasting" | "safety_only";
      retrieved_at_utc: string;
      uri?: string;
    }[];
  };
  layer_c_display_meta: {
    audience: "clinician_workstation";
    disclaimer_flags: {
      require_physician_review_banner: true;
      not_emergency_disposition: true;
      no_automatic_prescription: true;
      western_layer_non_gating: true;
      public_redaction_mode: false;
    };
    locale: string;
    copy_safe_summary_ref: string;
  };
};

function sha256Hex(text: string): string {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

function mapRiskGate(
  input: PatientConsultInputV1,
  evidenceAssessment: KmEvidenceAssessmentV1,
): MkmBianzhengTriLayerV1["layer_b_augmentation"]["western_med_fallback"]["risk_gate"] {
  const triage = input.lane_b_clinical.patient_intake_context?.triage_level;
  if (triage === "emergency") return "HOLD";
  const rf = input.lane_b_clinical.health_survey?.red_flag_notes?.trim();
  if (rf) return "WATCH";
  if (evidenceAssessment === "insufficient") return "HOLD";
  if (evidenceAssessment === "partial") return "WATCH";
  return "GO";
}

function mapLiteratureGrade(c: CdssCitationV1): "guideline" | "primary_lit" | "secondary_lit" | "other" {
  if (c.source_ref.toLowerCase().startsWith("epmc:")) return "primary_lit";
  if (c.evidence_level === "A") return "guideline";
  if (c.evidence_level === "B") return "secondary_lit";
  return "other";
}

function isLiteratureCitation(c: CdssCitationV1): boolean {
  return c.citation_id.startsWith("lit_") || c.source_ref.toLowerCase().startsWith("epmc:");
}

export function buildMkmBianzhengTriLayerFromConsult(
  input: PatientConsultInputV1,
  draft: ConsultDraftV1,
  evidenceAssessment: KmEvidenceAssessmentV1,
  generatedAtUtc?: string,
): MkmBianzhengTriLayerV1 {
  const at = generatedAtUtc || new Date().toISOString();
  const deterministicPayload = JSON.stringify({
    request_id: input.request_id,
    chief_complaint: input.lane_b_clinical.chief_complaint,
    onset: input.lane_b_clinical.onset,
    sasang: draft.profile_summary.sasang_candidate,
    syndrome: draft.reasoning.syndrome_hypothesis,
  });

  const score =
    evidenceAssessment === "sufficient" ? 0.62 : evidenceAssessment === "partial" ? 0.48 : 0.32;

  const literature = draft.citations
    .filter(isLiteratureCitation)
    .slice(0, 8)
    .map((c, idx) => {
      const excerpt = c.source_excerpt?.trim() || c.source_title;
      return {
        evidence_id: c.citation_id || `lit-${idx}`,
        corpus_id: "jema-ai-literature-runtime",
        corpus_snapshot_version: "consult_draft_v1",
        chunk_id: c.source_ref || c.citation_id,
        snippet_hash_sha256: sha256Hex(excerpt),
        evidence_grade: mapLiteratureGrade(c),
        claim_scope: "supporting" as const,
        retrieved_at_utc: at,
        uri: c.source_ref.startsWith("http") ? c.source_ref : undefined,
      };
    });

  const riskGate = mapRiskGate(input, evidenceAssessment);
  const urgency =
    input.lane_b_clinical.patient_intake_context?.triage_level === "emergency"
      ? ("emergency_evaluate_local_protocol" as const)
      : input.lane_b_clinical.patient_intake_context?.triage_level === "priority"
        ? ("urgent" as const)
        : ("routine" as const);

  return {
    schema: "mkm_bianzheng_tri_layer_v1",
    version: "1.0.0",
    layer_a_engine: {
      engine_id: "jema-ai-cdss-adapter",
      engine_version: "1.0.0",
      input_schema_id: "patient_consult_input_v1",
      input_schema_version: "1.0.0",
      ruleset_id: "jema_ai_bianzheng_assist_v1",
      ruleset_version: "2026-05-16",
      run_id: input.request_id,
      generated_at_utc: at,
      deterministic_input_sha256: sha256Hex(deterministicPayload),
      candidate_list: [
        {
          candidate_id: `cand-${draft.profile_summary.sasang_candidate}`,
          kind: "constitution_pattern",
          label: `Sasang assist candidate: ${draft.profile_summary.sasang_candidate}`,
          score_0_1: Math.min(0.85, score + 0.1),
          rank: 0,
          hypothesis_scope: "engine_hypothesis_only",
        },
        {
          candidate_id: "cand-syndrome-01",
          kind: "syndrome_pattern",
          label: draft.reasoning.syndrome_hypothesis.trim().slice(0, 400),
          score_0_1: score,
          rank: 1,
          hypothesis_scope: "engine_hypothesis_only",
        },
      ],
    },
    layer_b_augmentation: {
      western_med_fallback: {
        binding: "reference_only_non_diagnostic",
        risk_gate: riskGate,
        gate_rationale_ref: `jema-ai://cdss/risk/${input.request_id}`,
        differential_hypotheses: [
          {
            hypothesis_id: "wm-diff-syndrome-01",
            label: draft.reasoning.syndrome_hypothesis.trim().slice(0, 400),
            hypothesis_only: true,
            urgency,
          },
        ],
        contraindication_flags: [],
        escalation_prompts: [draft.reasoning.caution.trim()].filter((s) => s.length > 4),
      },
      literature_evidence: literature.length ? literature : [],
    },
    layer_c_display_meta: {
      audience: "clinician_workstation",
      disclaimer_flags: {
        require_physician_review_banner: true,
        not_emergency_disposition: true,
        no_automatic_prescription: true,
        western_layer_non_gating: true,
        public_redaction_mode: false,
      },
      locale: "ko-KR",
      copy_safe_summary_ref: `jema-ai://cdss/summary/${input.request_id}`,
    },
  };
}
