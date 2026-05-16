/**
 * Full CDS envelope pipeline: payload → Python validate → attach tri-layer.
 */

import type { ConsultDraftV1, PatientConsultInputV1 } from "./cdss-contract";
import {
  buildKmPhysicianCdsPayloadFromConsult,
  type BuildKmCdsPayloadOptions,
  type KmPhysicianCdsPayloadV1,
} from "./km-cds-envelope-adapter-v1";
import { validateKmCdsPayloadWithPython } from "./km-cds-envelope-python-bridge-v1";
import { buildMkmBianzhengTriLayerFromConsult } from "./km-cds-tri-layer-adapter-v1";

export type KmCdsEnvelopePipelineResult =
  | {
      ok: true;
      payload: KmPhysicianCdsPayloadV1;
      envelope: Record<string, unknown>;
      tri_layer: ReturnType<typeof buildMkmBianzhengTriLayerFromConsult>;
    }
  | {
      ok: false;
      payload: KmPhysicianCdsPayloadV1;
      tri_layer: ReturnType<typeof buildMkmBianzhengTriLayerFromConsult>;
      error: string;
    };

export function buildKmCdsEnvelopePipeline(
  input: PatientConsultInputV1,
  draft: ConsultDraftV1,
  options: BuildKmCdsPayloadOptions & { workspaceRoot?: string; skipPython?: boolean } = {},
): KmCdsEnvelopePipelineResult {
  const payload = buildKmPhysicianCdsPayloadFromConsult(input, draft, options);
  const triLayer = buildMkmBianzhengTriLayerFromConsult(
    input,
    draft,
    payload.evidence_assessment,
    options.retrievedAtUtc,
  );

  if (options.skipPython) {
    const envelope = {
      schema: "km_physician_cds_assist_envelope_v1",
      version: "1.0.0",
      intent: "physician_clinical_decision_support",
      boundary_ack: true,
      role_contract: {
        cds_only_not_standalone_diagnosis: true,
        physician_final_authority: true,
        not_emergency_disposition_final: true,
      },
      human_physician_review_required: true,
      ...payload,
      mkm_bianzheng_tri_layer: triLayer,
    };
    return { ok: true, payload, envelope, tri_layer: triLayer };
  }

  const validated = validateKmCdsPayloadWithPython(payload, options.workspaceRoot);
  if (!validated.ok) {
    return { ok: false, payload, tri_layer: triLayer, error: validated.error };
  }

  const envelope = {
    ...validated.envelope,
    mkm_bianzheng_tri_layer: triLayer,
  };
  return { ok: true, payload, envelope, tri_layer: triLayer };
}
