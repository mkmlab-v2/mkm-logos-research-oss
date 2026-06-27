import { NextRequest, NextResponse } from "next/server";

import { listPresetSummaries, loadLogosStudioPresets } from "@/lib/logosResearchStudioV1";
import { hasLogosProAccess, resolveLogosAccess } from "@/lib/logosResearchAccessV1";
import {
  LOGOS_FREE_DAILY_QUOTA,
  isLogosStudioQuotaDisabled,
  quotaRemaining,
  readQuotaState,
} from "@/lib/logosResearchQuotaV1";

export async function GET(request: NextRequest) {
  try {
    const doc = await loadLogosStudioPresets();
    const access = await resolveLogosAccess(request, "logos.presets.read");
    const pro = hasLogosProAccess(access);
    const quotaOff = isLogosStudioQuotaDisabled();
    const quotaState = readQuotaState(request);
    return NextResponse.json(
      {
        ok: true,
        schema: "logos_research_presets_v1",
        research_only: true,
        send_gate: "HOLD",
        free_daily_quota: LOGOS_FREE_DAILY_QUOTA,
        quota_disabled: quotaOff,
        remaining: quotaRemaining(quotaState, pro || quotaOff),
        pro: pro || quotaOff,
        presets: await listPresetSummaries(doc.presets),
        disclaimer: doc.disclaimer ?? null,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
