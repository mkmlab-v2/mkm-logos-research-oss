/**
 * @MKM12-METADATA
 * Type: Engine
 * Purpose: personadiary helpfulness feedback (B-track, append-only JSONL).
 */
import { NextRequest, NextResponse } from "next/server";
import {
  appendPersonalInsightFeedbackEvent,
  buildPersonalInsightFeedbackEvent,
  validatePersonalInsightFeedback,
} from "@/lib/personalInsightEvolutionFeedback";

type Body = {
  helpful?: boolean;
  surface?: string;
  clarity_score?: number;
  usefulness_score?: number;
  profile_id?: string;
  calendar_kst?: string;
  tags?: string[];
  free_text?: string;
  consent_feedback_use?: boolean;
  probe?: boolean;
};

const SURFACES = new Set(["daily_guide", "monthly_guide", "reflect"]);

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Body;
    if (typeof body.helpful !== "boolean") {
      return NextResponse.json({ ok: false, error: "helpful_required" }, { status: 400 });
    }
    const surface = (body.surface || "daily_guide").trim();
    if (!SURFACES.has(surface)) {
      return NextResponse.json({ ok: false, error: "surface_invalid" }, { status: 400 });
    }

    const input = {
      productLane: "personadiary" as const,
      surface: surface as "daily_guide" | "monthly_guide" | "reflect",
      helpful: body.helpful,
      clarityScore: body.clarity_score,
      usefulnessScore: body.usefulness_score,
      contentRef: {
        profileId: body.profile_id,
        calendarKst: body.calendar_kst,
        packageSchema: "personadiary_daily_response_package_v1",
      },
      tags: body.tags,
      freeText: body.free_text,
      consentFeedbackUse: body.consent_feedback_use,
      probe: body.probe,
    };
    const invalid = validatePersonalInsightFeedback(input);
    if (invalid) {
      return NextResponse.json({ ok: false, error: invalid }, { status: 400 });
    }

    const event = buildPersonalInsightFeedbackEvent(input);
    const storedAt = await appendPersonalInsightFeedbackEvent(event);

    return NextResponse.json(
      {
        ok: true,
        preview_only: true,
        hypothesis_tier: "B",
        non_gating: true,
        event_id: event.event_id,
        stored_at: storedAt,
      },
      { status: 200, headers: { "Cache-Control": "no-store" } }
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json(
      { ok: false, error: `feedback_submit_failed:${message}` },
      { status: 500 }
    );
  }
}
