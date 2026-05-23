/**
 * @MKM12-METADATA
 * Type: Engine
 * Purpose: clinician CDSS physician feedback (B-track, non-gating).
 */
import { NextRequest, NextResponse } from "next/server";
import {
  appendPersonalInsightFeedbackEvent,
  buildPersonalInsightFeedbackEvent,
  validatePersonalInsightFeedback,
  type PhysicianAction,
} from "@/lib/personalInsightEvolutionFeedback";

type Body = {
  helpful?: boolean;
  surface?: string;
  physician_action?: string;
  request_id?: string;
  clarity_score?: number;
  usefulness_score?: number;
  free_text?: string;
  consent_feedback_use?: boolean;
  probe?: boolean;
};

const SURFACES = new Set(["cds_draft", "patient_bundle"]);
const ACTIONS = new Set(["accept", "edit", "reject", "defer"]);

function isAction(value: string): value is PhysicianAction {
  return ACTIONS.has(value);
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Body;
    if (typeof body.helpful !== "boolean") {
      return NextResponse.json({ success: false, error: "helpful_required" }, { status: 400 });
    }
    const surface = (body.surface || "cds_draft").trim();
    if (!SURFACES.has(surface)) {
      return NextResponse.json({ success: false, error: "surface_invalid" }, { status: 400 });
    }
    const physicianAction = body.physician_action?.trim();
    if (physicianAction && !isAction(physicianAction)) {
      return NextResponse.json({ success: false, error: "physician_action_invalid" }, { status: 400 });
    }

    const input = {
      productLane: "clinician_cdss" as const,
      surface: surface as "cds_draft" | "patient_bundle",
      helpful: body.helpful,
      physicianAction: physicianAction as PhysicianAction | undefined,
      clarityScore: body.clarity_score,
      usefulnessScore: body.usefulness_score,
      contentRef: { requestId: body.request_id },
      freeText: body.free_text,
      consentFeedbackUse: body.consent_feedback_use,
      probe: body.probe,
    };
    const invalid = validatePersonalInsightFeedback(input);
    if (invalid) {
      return NextResponse.json({ success: false, error: invalid }, { status: 400 });
    }

    const event = buildPersonalInsightFeedbackEvent(input);
    const storedAt = await appendPersonalInsightFeedbackEvent(event);

    return NextResponse.json(
      {
        success: true,
        preview_only: true,
        hypothesis_tier: "B",
        non_gating: true,
        physician_confirmation_required: true,
        event_id: event.event_id,
        stored_at: storedAt,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } }
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json(
      { success: false, error: `physician_feedback_failed:${message}` },
      { status: 500 }
    );
  }
}
