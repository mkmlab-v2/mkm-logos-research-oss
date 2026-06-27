/**
 * no1kmedi 심플 코파일럿 v0 — 한의임상 Pack + IWS v2 4카드 응답.
 */
import { NextRequest, NextResponse } from "next/server";

import {
  clinicianDevUnlock,
  clinicianEmailFromRequest,
  clinicianProEnforceGate,
  resolveClinicianProAccess,
} from "@/lib/clinician-access-server-v1";
import {
  computeMedicalCalcFromSimpleCopilot,
  type SimpleCopilotRequestV1,
} from "@/lib/clinician-simple-copilot-v1";
import { runSimpleCopilotAdviceChain } from "@/lib/km-simple-copilot-chain-v1";

export async function POST(request: NextRequest) {
  try {
    const enforceProGate = clinicianProEnforceGate() && !clinicianDevUnlock() && process.env.KM_SIMPLE_COPILOT_REQUIRE_PRO === "1";
    if (enforceProGate) {
      const email = clinicianEmailFromRequest(request);
      if (!email) {
        return NextResponse.json(
          { success: false, error: "pro_clinical_assist_email_required" },
          { status: 403 },
        );
      }
      const access = await resolveClinicianProAccess(email);
      if (!access.unlocked) {
        return NextResponse.json(
          { success: false, error: "pro_clinical_assist_required" },
          { status: 403 },
        );
      }
    }

    const body = (await request.json()) as SimpleCopilotRequestV1;
    if (!body.request_id?.trim()) {
      return NextResponse.json({ success: false, error: "missing_request_id" }, { status: 400 });
    }
    const medicalCalc = computeMedicalCalcFromSimpleCopilot(body);
    const advice = await runSimpleCopilotAdviceChain(body);
    if (!advice.ok) {
      return NextResponse.json(
        { success: false, error: advice.error, stderr: advice.stderr },
        { status: advice.error === "invalid_birthdate" || advice.error === "missing_chief_complaint" ? 400 : 503 },
      );
    }

    return NextResponse.json(
      {
        success: true,
        track: "research_wellness_b",
        hypothesis_tier: "B",
        request_id: body.request_id,
        cards: advice.cards,
        medical_calc: medicalCalc,
        saju_calc: advice.sajuCalc,
        patient_education_copy: advice.patientEducationCopy,
        guardrail: {
          physician_confirmation_required: true,
          no_auto_trading_or_live_clinical_gating: true,
        },
      },
      { status: 200, headers: { "Cache-Control": "no-store, no-cache, must-revalidate" } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown";
    return NextResponse.json(
      { success: false, error: `simple_copilot_v1_failed: ${message}` },
      { status: 500 },
    );
  }
}
