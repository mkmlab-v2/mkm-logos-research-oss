/**
 * Offline adapter + optional Python Fact-Lock validation (no HTTP).
 *
 * Run from projects/no1kmedi:
 *   npm run smoke:km-cds-envelope-adapter
 */

import { buildKmCdsEnvelopePipeline } from "../src/lib/km-cds-envelope-pipeline-v1";
import type { ConsultDraftV1, PatientConsultInputV1 } from "../src/lib/cdss-contract";
import { resolveMkmWorkspaceRoot } from "../src/lib/km-cds-envelope-python-bridge-v1";

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exitCode = 1;
  }
}

const input: PatientConsultInputV1 = {
  schema: "patient_consult_input_v1",
  request_id: "adapter_smoke_001",
  actor_id: "adapter-smoke",
  lane_a_profile: {
    birth_instant_utc: "1987-12-31T15:00:00Z",
    iana_tz: "Asia/Seoul",
    constitution_survey: { digestion_pattern: "식후 더부룩함" },
  },
  lane_b_clinical: {
    chief_complaint: "만성 피로",
    onset: "6개월",
    severity: "중등도",
    medication: "없음",
    health_survey: { red_flag_notes: "흉부 불편 시 응급 평가 우선" },
  },
};

const draft: ConsultDraftV1 = {
  schema: "consult_draft_v1",
  request_id: input.request_id,
  mode: "cdss_draft",
  profile_summary: {
    sasang_candidate: "taeeum",
    saju_reference: "demo pillars",
    saju_source: "fallback",
  },
  clinical_summary: "주증상: 만성 피로 / onset 6개월",
  reasoning: {
    syndrome_hypothesis: "예비 병증 가설 (한의사 확인 필요)",
    care_direction: "문진 확장 후 변증 정교화. 생활 리듬 조정 검토.",
    caution: "응급 신호 시 대면 진료 우선.",
  },
  citations: [
    {
      citation_id: "canon_taeeum_001",
      source_title: "동의수세보원 · 태음인 편",
      source_excerpt: "태음인의 식적 경향은 소화와 수면을 함께 본다.",
      source_ref: "canon://donguisusebowon/taeeum/section-1",
      evidence_level: "A",
    },
    {
      citation_id: "lit_demo_001",
      source_title: "Demo literature",
      source_excerpt: "Supporting passage for smoke test.",
      source_ref: "epmc:demo-001",
      evidence_level: "B",
    },
  ],
  requires_physician_confirmation: true,
  non_medical_notice: "본 결과는 진료 보조 초안이며, 최종 진단·처방 판단은 한의사가 직접 확정해야 합니다.",
  generation: { llm_used: true },
};

const root = resolveMkmWorkspaceRoot();
if (!root) {
  console.error("MKM_WORKSPACE_ROOT required");
  process.exit(1);
}

const pipeline = buildKmCdsEnvelopePipeline(input, draft, { workspaceRoot: root });
assert(pipeline.ok, `pipeline: ${pipeline.ok ? "ok" : pipeline.error}`);
if (!pipeline.ok) {
  console.error(pipeline.error);
  process.exit(1);
}
assert(pipeline.payload.clinical_question.length >= 4, "clinical_question min length");
assert(Array.isArray(pipeline.payload.evidence_items) && pipeline.payload.evidence_items.length === 2, "evidence_items");
assert(pipeline.envelope.schema === "km_physician_cds_assist_envelope_v1", "envelope schema");
assert(pipeline.envelope.human_physician_review_required === true, "human review");
assert(pipeline.envelope.mkm_bianzheng_tri_layer != null, "tri_layer present");
assert(
  pipeline.tri_layer.schema === "mkm_bianzheng_tri_layer_v1",
  "tri_layer schema const",
);

if (process.exitCode === 1) {
  console.error("smoke-km-cds-envelope-adapter-v1: FAILED");
} else {
  console.log("smoke-km-cds-envelope-adapter-v1: OK");
}
