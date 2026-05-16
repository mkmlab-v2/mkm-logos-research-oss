/**
 * Offline: CDS envelope pipeline + patient_care_bundle Python chain (no HTTP).
 *
 *   MKM_WORKSPACE_ROOT=C:\workspace npm run smoke:patient-care-bundle-from-cds
 */

import fs from "node:fs";

import { buildKmCdsEnvelopePipeline } from "../src/lib/km-cds-envelope-pipeline-v1";
import type { ConsultDraftV1, PatientConsultInputV1 } from "../src/lib/cdss-contract";
import { resolveMkmWorkspaceRoot } from "../src/lib/km-cds-envelope-python-bridge-v1";
import {
  birthInstantToLocalParts,
  runPatientCareBundleFromCdsChain,
} from "../src/lib/km-patient-care-bundle-python-bridge-v1";

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exitCode = 1;
  }
}

const input: PatientConsultInputV1 = {
  schema: "patient_consult_input_v1",
  request_id: "bundle_smoke_001",
  actor_id: "bundle-smoke",
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
    health_survey: {},
  },
};

const draft: ConsultDraftV1 = {
  schema: "consult_draft_v1",
  request_id: input.request_id,
  mode: "cdss_draft",
  profile_summary: {
    sasang_candidate: "taeeum",
    saju_reference: "demo",
    saju_source: "fallback",
  },
  clinical_summary: "주증상: 만성 피로",
  reasoning: {
    syndrome_hypothesis: "예비 병증 가설",
    care_direction: "문진 확장 후 변증 정교화.",
    caution: "응급 신호 시 대면 진료.",
  },
  citations: [
    {
      citation_id: "canon_taeeum_001",
      source_title: "동의수세보원",
      source_excerpt: "태음인 소화 경향.",
      source_ref: "canon://donguisusebowon/taeeum/section-1",
      evidence_level: "A",
    },
  ],
  requires_physician_confirmation: true,
  non_medical_notice: "보조 초안.",
  generation: { llm_used: false, reason: "disabled" },
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
assert(pipeline.envelope.mkm_bianzheng_tri_layer != null, "tri_layer nested");

const local = birthInstantToLocalParts("1987-12-31T15:00:00Z", "Asia/Seoul");
const chain = runPatientCareBundleFromCdsChain(
  {
    requestId: input.request_id,
    cdsEnvelope: pipeline.envelope,
    birth: {
      year: local.year,
      month: local.month,
      day: local.day,
      hour: local.hour,
      minute: local.minute,
      second: local.second,
    },
    ianaTz: "Asia/Seoul",
    validateBundle: true,
    applySlotTemplates: true,
    validatePolicy: true,
    renderMdOut: true,
  },
  root,
);

assert(chain.ok, `chain: ${chain.ok ? "ok" : chain.error}`);
if (chain.ok) {
  assert(chain.bundle.schema === "patient_care_bundle_v1", "bundle schema");
  assert(
    typeof chain.bundle.provenance === "object" && chain.bundle.provenance != null,
    "bundle provenance",
  );
  const markdownPath = chain.markdownPath;
  if (typeof markdownPath !== "string" || markdownPath.length === 0) {
    console.error("FAIL: markdown path");
    process.exitCode = 1;
  } else {
    assert(fs.existsSync(markdownPath), "patient_facing md file exists");
    const md = fs.readFileSync(markdownPath, "utf-8");
    assert(md.trim().length > 20, "patient_facing md non-empty");
  }
}

if (process.exitCode === 1) {
  console.error("smoke-patient-care-bundle-from-cds-v1: FAILED");
} else {
  console.log("smoke-patient-care-bundle-from-cds-v1: OK");
  if (chain.ok) console.log(`  bundle: ${chain.bundlePath}`);
}
