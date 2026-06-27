import { NextRequest, NextResponse } from "next/server";

import { refreshClaimAttempt, requestOrigin } from "@/lib/logosAgentAuthV1";

export const runtime = "nodejs";

type ClaimBody = {
  claim_token?: string;
  email?: string;
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as ClaimBody;
    const claimToken = (body.claim_token || "").trim();
    if (!claimToken) {
      return NextResponse.json({ error: "claim_token_required" }, { status: 400 });
    }

    const result = await refreshClaimAttempt({
      claim_token: claimToken,
      email: body.email?.trim(),
      origin: requestOrigin(request.headers),
    });
    return NextResponse.json(result.body, { status: result.ok ? 200 : result.status });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
