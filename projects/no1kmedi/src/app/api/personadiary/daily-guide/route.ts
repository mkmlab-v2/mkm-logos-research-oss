/**
 * @MKM12-METADATA
 * Type: API
 * Purpose: PersonaDiary daily guide package (preview_only, read-only JSON).
 */
import { NextResponse } from "next/server";
import { loadDailyGuidePackage } from "@/lib/personadiaryDailyGuide";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const profileId = new URL(req.url).searchParams.get("profile_id");
  const doc = await loadDailyGuidePackage(profileId);
  if (!doc) {
    return NextResponse.json(
      {
        ok: false,
        error: "package_not_found",
        hint: "Run py scripts/build_commander_daily_fortune_v1.py from repo root",
      },
      { status: 404 }
    );
  }
  return NextResponse.json({
    ok: true,
    preview_only: true,
    hypothesis_tier: "B",
    non_gating: true,
    profile_id: profileId || process.env.NEXT_PUBLIC_PERSONADIARY_PROFILE_ID || "commander",
    package: doc,
  });
}
