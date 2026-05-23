/**
 * @MKM12-METADATA
 * Type: API
 * Purpose: PersonaDiary orb reflection — fuse user text with daily guide package.
 */
import { NextRequest, NextResponse } from "next/server";
import {
  buildReflectionText,
  loadDailyGuidePackage,
} from "@/lib/personadiaryDailyGuide";

export const dynamic = "force-dynamic";

type ReflectBody = {
  text?: string;
  profile_id?: string;
};

export async function POST(req: NextRequest) {
  let body: ReflectBody = {};
  try {
    body = (await req.json()) as ReflectBody;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }
  const text = typeof body.text === "string" ? body.text.trim() : "";
  if (!text) {
    return NextResponse.json({ ok: false, error: "text_required" }, { status: 400 });
  }
  if (text.length > 2000) {
    return NextResponse.json({ ok: false, error: "text_too_long" }, { status: 400 });
  }

  const profileId = body.profile_id?.trim() || null;
  const pkg = await loadDailyGuidePackage(profileId);
  if (!pkg) {
    return NextResponse.json(
      {
        ok: false,
        error: "package_not_found",
        reflection_ko:
          "오늘의 가이드가 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.",
      },
      { status: 503 }
    );
  }

  const reflection_ko = buildReflectionText(pkg, text);
  return NextResponse.json({
    ok: true,
    preview_only: true,
    hypothesis_tier: "B",
    non_gating: true,
    profile_id: profileId || process.env.NEXT_PUBLIC_PERSONADIARY_PROFILE_ID || "commander",
    calendar_kst: pkg.calendar_kst,
    reflection_ko,
    disclaimer_ko: pkg.disclaimer_ko,
  });
}
