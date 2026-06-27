import { NextRequest, NextResponse } from "next/server";

import { completeClaim } from "@/lib/logosAgentAuthV1";

export const runtime = "nodejs";

type CompleteBody = {
  claim_attempt_token?: string;
  user_code?: string;
  email?: string;
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as CompleteBody;
    const claimAttemptToken = (body.claim_attempt_token || "").trim();
    const userCode = (body.user_code || "").trim();
    if (!claimAttemptToken || !userCode) {
      return NextResponse.json(
        { error: "claim_attempt_token_and_user_code_required" },
        { status: 400 },
      );
    }

    const result = await completeClaim({
      claim_attempt_token: claimAttemptToken,
      user_code: userCode,
      email: body.email?.trim(),
    });
    return NextResponse.json(result.body, { status: result.ok ? 200 : result.status });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
