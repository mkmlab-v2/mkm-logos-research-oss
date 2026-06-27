import type { GraphReviewFeedback } from "./clinicianGraphTypesV1";
import { trackClinicianGraphReviewFeedback } from "./clinicianGraphPilotKpiV1";

export type SubmitGraphReviewFeedbackInput = {
  encounterRef: string;
  targetId: string;
  targetKind: "node" | "edge";
  feedback: GraphReviewFeedback;
  reasonCode?: string;
  clinicianNote?: string;
};

export async function submitGraphReviewFeedback(
  input: SubmitGraphReviewFeedbackInput,
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch("/api/clinician/graph/review-feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      schema: "clinician_graph_review_feedback_request_v1",
      encounter_ref: input.encounterRef,
      target_id: input.targetId,
      target_kind: input.targetKind,
      feedback: input.feedback,
      reason_code: input.reasonCode,
      clinician_note: input.clinicianNote,
    }),
  });
  const data = (await res.json()) as { success?: boolean; error?: string };
  if (!res.ok || !data.success) {
    return { success: false, error: data.error || "review_feedback_failed" };
  }
  trackClinicianGraphReviewFeedback(input.encounterRef, {
    target_id: input.targetId,
    feedback: input.feedback,
    reason_code: input.reasonCode,
  });
  return { success: true };
}
