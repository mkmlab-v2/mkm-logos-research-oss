/**
 * @MKM12-METADATA
 * Type: Engine
 * Purpose: Cross-surface personal_insight_evolution_feedback_v1 ingest (mkmlife CF forward).
 */
import { NextRequest, NextResponse } from "next/server";
import {
  appendPersonalInsightFeedbackEvent,
  buildPersonalInsightFeedbackEvent,
  type PersonalInsightFeedbackEvent,
  validatePersonalInsightFeedback,
  type PersonalInsightFeedbackInput,
} from "@/lib/personalInsightEvolutionFeedback";

type MkmlifeBody = {
  question_id?: string;
  user_id?: string;
  helpful?: boolean;
  clarity_score?: number;
  usefulness_score?: number;
  free_text?: string;
  consent_feedback_use?: boolean;
  probe?: boolean;
};

type RawEventBody = PersonalInsightFeedbackEvent;

function authorized(request: NextRequest, probe: boolean): boolean {
  const token = process.env.PERSONAL_INSIGHT_EVOLUTION_INGEST_TOKEN?.trim();
  if (!token) return probe;
  const header = request.headers.get("authorization")?.trim() || "";
  const bearer = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
  const alt = request.headers.get("x-piev1-ingest-token")?.trim() || "";
  return bearer === token || alt === token;
}

function eventFromMkmlife(body: MkmlifeBody): PersonalInsightFeedbackInput | null {
  if (typeof body.helpful !== "boolean") return null;
  if (!body.question_id?.trim() || !body.user_id?.trim()) return null;
  return {
    productLane: "mkmlife_one_question",
    surface: "one_question_report",
    helpful: body.helpful,
    clarityScore: body.clarity_score,
    usefulnessScore: body.usefulness_score,
    contentRef: {
      questionId: body.question_id.trim(),
      profileId: body.user_id.trim(),
    },
    freeText: body.free_text,
    consentFeedbackUse: body.consent_feedback_use,
    probe: body.probe,
  };
}

function isRawEvent(body: unknown): body is RawEventBody {
  if (!body || typeof body !== "object") return false;
  const row = body as RawEventBody;
  return row.schema === "personal_insight_evolution_feedback_v1" && typeof row.event_id === "string";
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as MkmlifeBody | RawEventBody;
    const probe =
      (body as MkmlifeBody).probe === true ||
      (isRawEvent(body) ? body.probe === true : false);

    if (!authorized(request, probe)) {
      return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
    }

    let event: PersonalInsightFeedbackEvent;
    if (isRawEvent(body)) {
      const invalid = validatePersonalInsightFeedback({
        productLane: body.product_lane,
        surface: body.surface,
        helpful: body.helpful,
        clarityScore: body.clarity_score,
        usefulnessScore: body.usefulness_score,
        physicianAction: body.physician_action,
        contentRef: body.content_ref
          ? {
              profileId: body.content_ref.profile_id,
              questionId: body.content_ref.question_id,
              requestId: body.content_ref.request_id,
              calendarKst: body.content_ref.calendar_kst,
              packageSchema: body.content_ref.package_schema,
            }
          : undefined,
        tags: body.tags,
        freeText: body.free_text,
        consentFeedbackUse: body.consent_feedback_use,
        probe: body.probe,
      });
      if (invalid) {
        return NextResponse.json({ ok: false, error: invalid }, { status: 400 });
      }
      event = body;
    } else {
      const input = eventFromMkmlife(body as MkmlifeBody);
      if (!input) {
        return NextResponse.json({ ok: false, error: "invalid_mkmlife_payload" }, { status: 400 });
      }
      const invalid = validatePersonalInsightFeedback(input);
      if (invalid) {
        return NextResponse.json({ ok: false, error: invalid }, { status: 400 });
      }
      event = buildPersonalInsightFeedbackEvent(input);
    }

    const storedAt = await appendPersonalInsightFeedbackEvent(event);
    return NextResponse.json(
      {
        ok: true,
        preview_only: true,
        hypothesis_tier: "B",
        non_gating: true,
        event_id: event.event_id,
        stored_at: storedAt,
        storage: "no1kmedi_jsonl",
      },
      { status: 200, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json(
      { ok: false, error: `ingest_failed:${message}` },
      { status: 500 },
    );
  }
}
