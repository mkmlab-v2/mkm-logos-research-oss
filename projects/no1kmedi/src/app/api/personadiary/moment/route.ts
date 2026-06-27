/**
 * @MKM12-METADATA
 * Type: API
 * Purpose: PersonaDiary moment Q&A — intent routing over daily package (Phase B).
 */
import { NextRequest, NextResponse } from "next/server";
import { loadDailyGuidePackage } from "@/lib/personadiaryDailyGuide";
import { assembleMomentResponse } from "@/lib/personadiaryMoment";
import { polishMomentRuntime } from "@/lib/personadiaryMomentPolishV1";

export const dynamic = "force-dynamic";

type MomentBody = {
  text?: string;
  query?: string;
  profile_id?: string;
  survey_responses?: Record<string, number>;
};

export async function POST(req: NextRequest) {
  let body: MomentBody = {};
  try {
    body = (await req.json()) as MomentBody;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const text = (typeof body.text === "string" ? body.text : body.query || "").trim();
  if (!text) {
    return NextResponse.json({ ok: false, error: "text_required" }, { status: 400 });
  }
  if (text.length > 2000) {
    return NextResponse.json({ ok: false, error: "text_too_long" }, { status: 400 });
  }

  const profileId = body.profile_id?.trim() || null;
  const surveyResponses =
    body.survey_responses && typeof body.survey_responses === "object"
      ? Object.fromEntries(
          Object.entries(body.survey_responses).filter(
            (entry): entry is [string, number] => typeof entry[1] === "number"
          )
        )
      : undefined;
  const pkg = await loadDailyGuidePackage(profileId);
  if (!pkg || pkg.schema !== "personadiary_daily_response_package_v1") {
    return NextResponse.json(
      {
        ok: false,
        error: "package_not_found",
        hint: "Run scripts/Run-PersonadiaryDailyGuideRefresh_v1.ps1",
      },
      { status: 503 }
    );
  }

  const moment = await polishMomentRuntime(
    assembleMomentResponse(pkg, text, undefined, {
      requestProfileId: profileId,
      surveyResponses,
    }),
    text
  );
  return NextResponse.json({
    ok: true,
    preview_only: true,
    hypothesis_tier: "B",
    non_gating: true,
    profile_id:
      profileId || process.env.NEXT_PUBLIC_PERSONADIARY_PROFILE_ID || "commander",
    moment,
  });
}
