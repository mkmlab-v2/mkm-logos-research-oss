import type { GraphBuildResponse, GraphBundleV1 } from "./clinicianGraphTypesV1";

type BuildGraphInput = {
  requestId: string;
  envelope: Record<string, unknown>;
  reasoning?: {
    syndrome_hypothesis?: string;
    care_direction?: string;
    caution?: string;
  };
  patientCareBundle?: Record<string, unknown> | null;
};

export async function fetchClinicianGraphFromCds(input: BuildGraphInput): Promise<GraphBundleV1> {
  const res = await fetch("/api/clinician/graph/build-from-cds", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      schema: "clinician_graph_build_from_cds_request_v1",
      request_id: input.requestId,
      cds_envelope: input.envelope,
      reasoning: input.reasoning,
      patient_care_bundle: input.patientCareBundle || undefined,
      options: {
        include_sasang_hint: true,
        include_conflict_paths: true,
        include_bundle_slots: Boolean(input.patientCareBundle),
      },
    }),
  });
  const data = (await res.json()) as GraphBuildResponse;
  if (!res.ok || !data.success || !data.graph_bundle_v1) {
    throw new Error(data.error || "graph_build_failed");
  }
  return data.graph_bundle_v1;
}
