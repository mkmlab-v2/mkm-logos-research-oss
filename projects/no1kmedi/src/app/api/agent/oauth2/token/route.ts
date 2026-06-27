import { NextRequest, NextResponse } from "next/server";

import { LOGOS_AGENT_AUTH_GRANT_CLAIM } from "@/lib/logosAgentAuthTypesV1";
import { exchangeClaimToken } from "@/lib/logosAgentAuthV1";

export const runtime = "nodejs";

async function parseTokenBody(request: NextRequest): Promise<Record<string, string>> {
  const contentType = request.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const json = (await request.json()) as Record<string, string>;
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(json)) {
      if (typeof v === "string") out[k] = v;
    }
    return out;
  }
  const text = await request.text();
  const params = new URLSearchParams(text);
  const out: Record<string, string> = {};
  for (const [k, v] of params.entries()) out[k] = v;
  return out;
}

export async function POST(request: NextRequest) {
  try {
    const body = await parseTokenBody(request);
    const grantType = (body.grant_type || "").trim();
    if (grantType !== LOGOS_AGENT_AUTH_GRANT_CLAIM) {
      return NextResponse.json({ error: "unsupported_grant_type" }, { status: 400 });
    }
    const claimToken = (body.claim_token || "").trim();
    if (!claimToken) {
      return NextResponse.json({ error: "claim_token_required" }, { status: 400 });
    }

    const result = await exchangeClaimToken(claimToken);
    return NextResponse.json(result.body, { status: result.ok ? 200 : result.status });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown_error";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
