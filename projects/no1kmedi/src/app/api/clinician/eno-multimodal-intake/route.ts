/**
 * Clinician lane: Eno multimodal intake preview (physician_gold · human_confirm).
 */

import { NextRequest, NextResponse } from "next/server";
import {
  buildEnoMultimodalIntakeSnapshot,
  parseEnoHealthPayload,
  type EnoHealthData,
} from "@/lib/eno-multimodal-intake-v1";

type RequestBody = {
  health_data?: EnoHealthData;
  payload?: unknown;
  include_guardian_analysis?: boolean;
  source?: "eno_pwa" | "paste_json" | "local_storage";
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as RequestBody;
    const parsed = parseEnoHealthPayload(body.health_data ? { health_data: body.health_data } : body.payload ?? body);
    if (!parsed.ok) {
      return NextResponse.json({ success: false, error: parsed.error }, { status: 400 });
    }

    let guardianMessage: string | undefined;
    if (body.include_guardian_analysis) {
      const origin = request.nextUrl.origin;
      const guardianRes = await fetch(`${origin}/api/guardian/ai-guardian`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ health_data: parsed.data }),
      });
      const guardianJson = (await guardianRes.json().catch(() => ({}))) as {
        success?: boolean;
        analysis?: { message?: string };
      };
      if (guardianRes.ok && guardianJson.success && guardianJson.analysis?.message) {
        guardianMessage = guardianJson.analysis.message;
      }
    }

    const snapshot = buildEnoMultimodalIntakeSnapshot(
      parsed.data,
      body.source ?? "paste_json",
      guardianMessage,
    );

    return NextResponse.json({
      success: true,
      preview: snapshot,
      track: "physician_gold",
      human_confirm_required: true,
    });
  } catch {
    return NextResponse.json({ success: false, error: "eno_multimodal_intake_failed" }, { status: 500 });
  }
}
